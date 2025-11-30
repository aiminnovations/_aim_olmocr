"""
PDF processing worker using olmOCR pipeline.
"""

import asyncio
import hashlib
import json
import logging
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from google.cloud import firestore, storage
from pypdf import PdfReader

from olmocr.data.renderpdf import render_pdf_to_base64png
from olmocr.prompts import PageResponse, build_no_anchoring_v4_yaml_prompt
from olmocr.train.dataloader import FrontMatterParser

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class PageResult:
    """Result of processing a single page."""
    page_num: int
    text: str
    metadata: Dict[str, Any]
    input_tokens: int
    output_tokens: int
    is_fallback: bool = False


@dataclass
class ProcessingResult:
    """Result of processing a PDF."""
    pages: List[PageResult]
    total_input_tokens: int
    total_output_tokens: int
    total_pages: int
    fallback_pages: int
    processing_time_ms: int


class OlmOCRProcessor:
    """Processor for running olmOCR on PDFs."""

    def __init__(self):
        self.storage_client = storage.Client()
        self.firestore_client = firestore.AsyncClient(project=config.gcp_project_id)
        self.bucket = self.storage_client.bucket(config.gcs_bucket)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def process_job(self, job_data: Dict[str, Any]) -> None:
        """Process a single job from the queue."""
        job_id = job_data["job_id"]
        user_id = job_data["user_id"]
        input_path = job_data["input_path"]
        output_path = job_data["output_path"]
        output_format = job_data.get("output_format", "markdown")
        options = job_data.get("options", {})

        logger.info(f"Processing job {job_id} for user {user_id}")

        try:
            # Update job status to processing
            await self._update_job_status(job_id, "processing")

            start_time = time.time()

            # Download PDF from GCS
            with tempfile.TemporaryDirectory() as temp_dir:
                local_pdf = Path(temp_dir) / "input.pdf"
                gcs_path = f"users/{user_id}/{input_path}"

                logger.info(f"Downloading PDF from gs://{config.gcs_bucket}/{gcs_path}")
                blob = self.bucket.blob(gcs_path)
                blob.download_to_filename(str(local_pdf))

                # Get page count
                reader = PdfReader(str(local_pdf))
                num_pages = len(reader.pages)

                logger.info(f"PDF has {num_pages} pages")

                # Update job with page count
                await self._update_job_input(job_id, num_pages, local_pdf.stat().st_size)

                # Process PDF
                result = await self._process_pdf(
                    str(local_pdf),
                    job_id,
                    num_pages,
                )

                # Generate output based on format
                output_files = await self._generate_output(
                    result,
                    user_id,
                    output_path,
                    output_format,
                    input_path,
                    options,
                )

                processing_time_ms = int((time.time() - start_time) * 1000)

                # Update job as completed
                await self._update_job_completed(
                    job_id,
                    output_files,
                    result.total_input_tokens,
                    result.total_output_tokens,
                    processing_time_ms,
                )

                logger.info(
                    f"Job {job_id} completed: {num_pages} pages, "
                    f"{result.total_input_tokens} input tokens, "
                    f"{result.total_output_tokens} output tokens, "
                    f"{processing_time_ms}ms"
                )

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            await self._update_job_status(job_id, "failed", error=str(e))
            raise

    async def _process_pdf(
        self,
        pdf_path: str,
        job_id: str,
        num_pages: int,
    ) -> ProcessingResult:
        """Process all pages of a PDF."""
        pages: List[PageResult] = []
        total_input_tokens = 0
        total_output_tokens = 0
        fallback_pages = 0

        # Process pages with concurrency limit
        semaphore = asyncio.Semaphore(config.max_concurrent_pages)

        async def process_page_with_semaphore(page_num: int) -> PageResult:
            async with semaphore:
                return await self._process_page(pdf_path, page_num)

        # Process all pages
        tasks = [process_page_with_semaphore(i) for i in range(num_pages)]

        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                result = await task
                pages.append(result)

                total_input_tokens += result.input_tokens
                total_output_tokens += result.output_tokens
                if result.is_fallback:
                    fallback_pages += 1

                # Update progress
                await self._update_job_progress(job_id, len(pages), num_pages)

            except Exception as e:
                logger.error(f"Error processing page: {e}")
                # Create fallback result
                pages.append(PageResult(
                    page_num=i,
                    text=f"[Error processing page {i + 1}]",
                    metadata={},
                    input_tokens=0,
                    output_tokens=0,
                    is_fallback=True,
                ))
                fallback_pages += 1

        # Sort pages by page number
        pages.sort(key=lambda p: p.page_num)

        return ProcessingResult(
            pages=pages,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_pages=num_pages,
            fallback_pages=fallback_pages,
            processing_time_ms=0,  # Set by caller
        )

    async def _process_page(
        self,
        pdf_path: str,
        page_num: int,
    ) -> PageResult:
        """Process a single page."""
        # Render page to image
        image_base64 = await asyncio.to_thread(
            render_pdf_to_base64png,
            pdf_path,
            page_num,
            target_longest_image_dim=config.target_longest_image_dim,
        )

        # Build query for vLLM
        query = {
            "model": config.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": build_no_anchoring_v4_yaml_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 8000,
            "temperature": 0.1,
        }

        # Send to API (Parasail or local vLLM)
        async with self.session.post(
            config.api_endpoint,
            json=query,
            headers=config.api_headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"API request failed ({response.status}): {error_text}")

            result = await response.json()

        # Parse response
        content = result["choices"][0]["message"]["content"]
        input_tokens = result["usage"]["prompt_tokens"]
        output_tokens = result["usage"]["completion_tokens"]

        # Parse YAML front matter and extract text
        try:
            parser = FrontMatterParser(content)
            text = parser.body
            metadata = {
                "primary_language": parser.get("primary_language"),
                "is_rotation_valid": parser.get("is_rotation_valid"),
                "rotation_correction": parser.get("rotation_correction"),
                "is_table": parser.get("is_table"),
                "is_diagram": parser.get("is_diagram"),
            }
        except Exception as e:
            logger.warning(f"Failed to parse front matter: {e}")
            text = content
            metadata = {}

        return PageResult(
            page_num=page_num,
            text=text,
            metadata=metadata,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def _generate_output(
        self,
        result: ProcessingResult,
        user_id: str,
        output_path: str,
        output_format: str,
        input_filename: str,
        options: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate output files based on format."""
        output_files = []

        # Get base filename without extension
        base_name = Path(input_filename).stem

        if output_format == "markdown":
            # Combine all pages into single markdown file
            full_text = "\n\n---\n\n".join(p.text for p in result.pages)

            # Add metadata header if requested
            if options.get("include_metadata", True):
                header = f"""---
source: {input_filename}
pages: {result.total_pages}
processed: {datetime.utcnow().isoformat()}
---

"""
                full_text = header + full_text

            # Upload to GCS
            output_file = f"{output_path}/{base_name}.md"
            await self._upload_output(user_id, output_file, full_text.encode())

            output_files.append({
                "name": f"{base_name}.md",
                "path": output_file,
                "size": len(full_text.encode()),
            })

        elif output_format == "json":
            # Generate JSON output
            json_output = {
                "source": input_filename,
                "pages": result.total_pages,
                "processed": datetime.utcnow().isoformat(),
                "content": [
                    {
                        "page": p.page_num + 1,
                        "text": p.text,
                        "metadata": p.metadata,
                    }
                    for p in result.pages
                ],
                "metrics": {
                    "input_tokens": result.total_input_tokens,
                    "output_tokens": result.total_output_tokens,
                    "fallback_pages": result.fallback_pages,
                },
            }

            json_bytes = json.dumps(json_output, indent=2).encode()
            output_file = f"{output_path}/{base_name}.json"
            await self._upload_output(user_id, output_file, json_bytes)

            output_files.append({
                "name": f"{base_name}.json",
                "path": output_file,
                "size": len(json_bytes),
            })

        elif output_format == "dolma":
            # Generate Dolma format
            full_text = "\n\n".join(p.text for p in result.pages)
            text_hash = hashlib.sha1(full_text.encode()).hexdigest()

            dolma_doc = {
                "id": text_hash,
                "text": full_text,
                "source": "olmocr-gcp",
                "added": datetime.utcnow().strftime("%Y-%m-%d"),
                "created": datetime.utcnow().strftime("%Y-%m-%d"),
                "metadata": {
                    "Source-File": input_filename,
                    "pdf-pages": result.total_pages,
                    "total-input-tokens": result.total_input_tokens,
                    "total-output-tokens": result.total_output_tokens,
                    "total-fallback-pages": result.fallback_pages,
                },
                "attributes": {
                    "pdf_page_numbers": [
                        [sum(len(p.text) for p in result.pages[:i]),
                         sum(len(p.text) for p in result.pages[:i+1]),
                         i + 1]
                        for i in range(len(result.pages))
                    ],
                    "primary_language": [p.metadata.get("primary_language") for p in result.pages],
                    "is_table": [p.metadata.get("is_table", False) for p in result.pages],
                },
            }

            dolma_bytes = (json.dumps(dolma_doc) + "\n").encode()
            output_file = f"{output_path}/{base_name}.jsonl"
            await self._upload_output(user_id, output_file, dolma_bytes)

            output_files.append({
                "name": f"{base_name}.jsonl",
                "path": output_file,
                "size": len(dolma_bytes),
            })

        elif output_format == "html":
            # Generate HTML output
            pages_html = "\n".join(
                f'<div class="page" data-page="{p.page_num + 1}">'
                f'<h3>Page {p.page_num + 1}</h3>'
                f'<div class="content">{p.text}</div>'
                f'</div>'
                for p in result.pages
            )

            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{base_name}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .page {{ margin-bottom: 40px; padding: 20px; border: 1px solid #ddd; }}
        .page h3 {{ margin-top: 0; color: #666; }}
        .content {{ white-space: pre-wrap; }}
    </style>
</head>
<body>
    <h1>{base_name}</h1>
    <p>Processed: {datetime.utcnow().isoformat()}</p>
    <p>Pages: {result.total_pages}</p>
    <hr>
    {pages_html}
</body>
</html>"""

            html_bytes = html_content.encode()
            output_file = f"{output_path}/{base_name}.html"
            await self._upload_output(user_id, output_file, html_bytes)

            output_files.append({
                "name": f"{base_name}.html",
                "path": output_file,
                "size": len(html_bytes),
            })

        return output_files

    async def _upload_output(
        self,
        user_id: str,
        path: str,
        content: bytes,
    ) -> None:
        """Upload output file to GCS."""
        gcs_path = f"users/{user_id}/{path}"
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(content)
        logger.info(f"Uploaded output to gs://{config.gcs_bucket}/{gcs_path}")

    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """Update job status in Firestore."""
        doc_ref = self.firestore_client.collection("jobs").document(job_id)

        update_data = {
            "status": status,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        if status == "processing":
            update_data["started_at"] = firestore.SERVER_TIMESTAMP
        elif status in ("completed", "failed"):
            update_data["completed_at"] = firestore.SERVER_TIMESTAMP

        if error:
            update_data["error"] = error

        await doc_ref.update(update_data)

    async def _update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int,
    ) -> None:
        """Update job progress in Firestore."""
        percentage = int((current / total) * 100) if total > 0 else 0

        doc_ref = self.firestore_client.collection("jobs").document(job_id)
        await doc_ref.update({
            "progress": {
                "current": current,
                "total": total,
                "percentage": percentage,
            },
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    async def _update_job_input(
        self,
        job_id: str,
        page_count: int,
        file_size: int,
    ) -> None:
        """Update job input metadata."""
        doc_ref = self.firestore_client.collection("jobs").document(job_id)
        await doc_ref.update({
            "input.page_count": page_count,
            "input.file_size": file_size,
            "progress.total": page_count,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    async def _update_job_completed(
        self,
        job_id: str,
        output_files: List[Dict[str, Any]],
        input_tokens: int,
        output_tokens: int,
        processing_time_ms: int,
    ) -> None:
        """Update job as completed with metrics."""
        doc_ref = self.firestore_client.collection("jobs").document(job_id)
        await doc_ref.update({
            "status": "completed",
            "completed_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "output.files": output_files,
            "metrics": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "processing_time_ms": processing_time_ms,
            },
        })
