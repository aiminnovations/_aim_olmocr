#!/usr/bin/env python3
"""
olmOCR Batch Processor v2.0

A high-performance web app for batch processing PDFs using olmOCR via Parasail API.
Features:
- Parallel page processing (5-10x faster)
- Persistent jobs via Google Cloud Firestore (survive page refresh/close)
- Folder uploads with structure preservation
- Configurable output locations
- Batch grouping for organized processing

Usage:
    pip install -r requirements.txt
    python app.py

Then open http://localhost:8080 in your browser.
"""

import asyncio
import base64
import io
import json
import os
import uuid
from typing import List, Optional, Dict
from datetime import datetime
from contextlib import asynccontextmanager

import aiohttp
from google.cloud import firestore
from google.cloud import storage
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pdf2image import convert_from_bytes
from PIL import Image

# ============================================
# Configuration
# ============================================

PARASAIL_API_KEY = os.environ.get("PARASAIL_API_KEY", "")
PARASAIL_API_URL = "https://api.parasail.io/v1/chat/completions"
PARASAIL_MODEL = "allenai/olmOCR-2-7B-1025"

# Performance settings
MAX_CONCURRENT_PAGES = int(os.environ.get("MAX_CONCURRENT_PAGES", "5"))
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", "3"))
RENDER_DPI = int(os.environ.get("RENDER_DPI", "120"))
IMAGE_QUALITY = int(os.environ.get("IMAGE_QUALITY", "85"))

# GCP Configuration
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "")  # For PDF storage

# Firestore collection names
BATCHES_COLLECTION = "ocr_batches"
JOBS_COLLECTION = "ocr_jobs"
PAGES_COLLECTION = "ocr_pages"

# ============================================
# Firestore Client
# ============================================

db: Optional[firestore.AsyncClient] = None
gcs_client: Optional[storage.Client] = None


def get_firestore() -> firestore.AsyncClient:
    """Get Firestore async client."""
    global db
    if db is None:
        if GCP_PROJECT_ID:
            db = firestore.AsyncClient(project=GCP_PROJECT_ID)
        else:
            db = firestore.AsyncClient()
    return db


def get_gcs_client() -> Optional[storage.Client]:
    """Get GCS client for PDF storage."""
    global gcs_client
    if gcs_client is None and GCS_BUCKET:
        gcs_client = storage.Client()
    return gcs_client


# ============================================
# App Setup
# ============================================

# Global state for active processing
active_tasks: Dict[str, asyncio.Task] = {}
job_semaphore: Optional[asyncio.Semaphore] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    global job_semaphore

    # Startup
    job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

    # Test Firestore connection
    try:
        fs = get_firestore()
        # Simple test query
        await fs.collection(BATCHES_COLLECTION).limit(1).get()
        print("Connected to Firestore successfully")
    except Exception as e:
        print(f"Warning: Firestore connection issue: {e}")

    # Resume any interrupted jobs
    asyncio.create_task(resume_pending_jobs())

    yield

    # Shutdown - cancel active tasks
    for task in active_tasks.values():
        task.cancel()


app = FastAPI(title="olmOCR Batch Processor", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Firestore Data Operations
# ============================================

async def save_batch(batch: dict):
    """Save batch to Firestore."""
    fs = get_firestore()
    await fs.collection(BATCHES_COLLECTION).document(batch['id']).set(batch)


async def get_batch(batch_id: str) -> Optional[dict]:
    """Get batch from Firestore."""
    fs = get_firestore()
    doc = await fs.collection(BATCHES_COLLECTION).document(batch_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


async def delete_batch_doc(batch_id: str):
    """Delete batch from Firestore."""
    fs = get_firestore()
    await fs.collection(BATCHES_COLLECTION).document(batch_id).delete()


async def list_batches() -> List[dict]:
    """List all batches."""
    fs = get_firestore()
    # Don't use order_by to avoid needing Firestore composite indexes
    docs = await fs.collection(BATCHES_COLLECTION).get()
    batches = [doc.to_dict() for doc in docs]
    # Sort in Python instead
    batches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return batches


async def save_job(job: dict):
    """Save job to Firestore."""
    fs = get_firestore()
    await fs.collection(JOBS_COLLECTION).document(job['id']).set(job)


async def get_job(job_id: str) -> Optional[dict]:
    """Get job from Firestore."""
    fs = get_firestore()
    doc = await fs.collection(JOBS_COLLECTION).document(job_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


async def delete_job_doc(job_id: str):
    """Delete job and its pages from Firestore."""
    fs = get_firestore()

    # Delete pages
    pages = await fs.collection(PAGES_COLLECTION).where(
        'job_id', '==', job_id
    ).get()
    for page_doc in pages:
        await page_doc.reference.delete()

    # Delete job
    await fs.collection(JOBS_COLLECTION).document(job_id).delete()

    # Delete PDF from GCS if exists
    await delete_pdf(job_id)


async def get_batch_jobs(batch_id: str) -> List[dict]:
    """Get all jobs for a batch."""
    fs = get_firestore()
    # Don't combine where + order_by to avoid needing Firestore composite indexes
    docs = await fs.collection(JOBS_COLLECTION).where(
        'batch_id', '==', batch_id
    ).get()
    jobs = [doc.to_dict() for doc in docs]
    # Sort in Python instead
    jobs.sort(key=lambda x: x.get('created_at', ''))
    return jobs


async def save_page(job_id: str, page_num: int, page_data: dict):
    """Save page result to Firestore."""
    fs = get_firestore()
    page_id = f"{job_id}_page_{page_num}"
    page_data['job_id'] = job_id
    await fs.collection(PAGES_COLLECTION).document(page_id).set(page_data)


async def get_pages(job_id: str) -> List[dict]:
    """Get all pages for a job."""
    fs = get_firestore()
    # Don't combine where + order_by to avoid needing Firestore composite indexes
    docs = await fs.collection(PAGES_COLLECTION).where(
        'job_id', '==', job_id
    ).get()
    pages = [doc.to_dict() for doc in docs]
    # Sort in Python instead
    pages.sort(key=lambda x: x.get('page_num', 0))
    return pages


# ============================================
# PDF Storage (Google Cloud Storage)
# ============================================

async def store_pdf(job_id: str, pdf_bytes: bytes):
    """Store PDF bytes in GCS or memory."""
    client = get_gcs_client()
    if client and GCS_BUCKET:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.bucket(GCS_BUCKET).blob(f"pdfs/{job_id}.pdf").upload_from_string(
                pdf_bytes, content_type='application/pdf'
            )
        )
    else:
        # Fallback: store in Firestore (for small PDFs < 1MB)
        # Note: Firestore has 1MB document limit
        fs = get_firestore()
        await fs.collection('pdf_storage').document(job_id).set({
            'data': base64.b64encode(pdf_bytes).decode('utf-8')
        })


async def load_pdf(job_id: str) -> Optional[bytes]:
    """Load PDF bytes from GCS or memory."""
    client = get_gcs_client()
    if client and GCS_BUCKET:
        loop = asyncio.get_event_loop()
        try:
            blob = client.bucket(GCS_BUCKET).blob(f"pdfs/{job_id}.pdf")
            return await loop.run_in_executor(None, blob.download_as_bytes)
        except Exception:
            return None
    else:
        # Fallback: load from Firestore
        fs = get_firestore()
        doc = await fs.collection('pdf_storage').document(job_id).get()
        if doc.exists:
            data = doc.to_dict().get('data')
            if data:
                return base64.b64decode(data)
    return None


async def delete_pdf(job_id: str):
    """Delete stored PDF."""
    client = get_gcs_client()
    if client and GCS_BUCKET:
        loop = asyncio.get_event_loop()
        try:
            blob = client.bucket(GCS_BUCKET).blob(f"pdfs/{job_id}.pdf")
            await loop.run_in_executor(None, blob.delete)
        except Exception:
            pass
    else:
        # Fallback: delete from Firestore
        fs = get_firestore()
        await fs.collection('pdf_storage').document(job_id).delete()


async def save_output(job_id: str, output_text: str):
    """Save job output to Firestore."""
    fs = get_firestore()
    await fs.collection('outputs').document(job_id).set({
        'text': output_text,
        'created_at': datetime.now().isoformat()
    })


async def get_output(job_id: str) -> Optional[str]:
    """Get job output from Firestore."""
    fs = get_firestore()
    doc = await fs.collection('outputs').document(job_id).get()
    if doc.exists:
        return doc.to_dict().get('text')
    return None


# ============================================
# olmOCR Processing (Optimized)
# ============================================

def get_ocr_prompt():
    """Get the olmOCR prompt."""
    return (
        "Below is the image of one page of a document. "
        "Just return the plain text representation of this document "
        "as if you were reading it naturally.\n"
        "Do not hallucinate.\n\n"
        "Return the text in markdown format."
    )


def render_all_pages(pdf_bytes: bytes, dpi: int = RENDER_DPI) -> List[Image.Image]:
    """Render all PDF pages at once (much faster than one-by-one)."""
    images = convert_from_bytes(pdf_bytes, dpi=dpi)

    processed = []
    max_dim = 1568

    for img in images:
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        processed.append(img)

    return processed


def image_to_base64(img: Image.Image, quality: int = IMAGE_QUALITY) -> str:
    """Convert image to base64 JPEG (smaller than PNG)."""
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode()


async def process_single_page(
    session: aiohttp.ClientSession,
    image_base64: str,
    page_num: int,
    semaphore: asyncio.Semaphore
) -> dict:
    """Process a single page via Parasail API with rate limiting."""

    async with semaphore:
        payload = {
            "model": PARASAIL_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": get_ocr_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1
        }

        headers = {
            "Authorization": f"Bearer {PARASAIL_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            async with session.post(
                PARASAIL_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise Exception(f"API error ({response.status}): {error}")

                result = await response.json()
                text = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})

                return {
                    "page_num": page_num + 1,
                    "text": text,
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "error": None
                }
        except asyncio.TimeoutError:
            return {
                "page_num": page_num + 1,
                "text": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "error": "Request timed out"
            }
        except Exception as e:
            return {
                "page_num": page_num + 1,
                "text": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "error": str(e)
            }


async def update_job_progress(job_id: str, current_page: int, total_pages: int):
    """Update job progress in Firestore."""
    job = await get_job(job_id)
    if job:
        progress = int((current_page / total_pages) * 100) if total_pages > 0 else 0
        job['current_page'] = current_page
        job['progress'] = progress
        await save_job(job)


async def process_job(job_id: str):
    """Process a single job with parallel page processing."""
    global job_semaphore

    if job_semaphore is None:
        job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

    async with job_semaphore:
        try:
            job = await get_job(job_id)
            if not job:
                return

            job['status'] = 'processing'
            job['started_at'] = datetime.now().isoformat()
            await save_job(job)

            pdf_bytes = await load_pdf(job_id)
            if not pdf_bytes:
                raise Exception("PDF file not found")

            loop = asyncio.get_event_loop()
            images = await loop.run_in_executor(None, render_all_pages, pdf_bytes)
            num_pages = len(images)

            job['total_pages'] = num_pages
            await save_job(job)

            def convert_images(imgs):
                return [image_to_base64(img) for img in imgs]

            base64_images = await loop.run_in_executor(
                None,
                convert_images,
                images
            )

            del images

            page_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
            completed_pages = 0

            async with aiohttp.ClientSession() as session:
                tasks = [
                    process_single_page(session, img_b64, page_num, page_semaphore)
                    for page_num, img_b64 in enumerate(base64_images)
                ]

                results = []
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    results.append(result)
                    completed_pages += 1

                    await save_page(job_id, result['page_num'], result)
                    await update_job_progress(job_id, completed_pages, num_pages)

            results.sort(key=lambda x: x["page_num"])

            full_text = "\n\n---\n\n".join(
                f"## Page {r['page_num']}\n\n{r['text']}" if not r.get('error')
                else f"## Page {r['page_num']}\n\n[Error: {r['error']}]"
                for r in results
            )

            total_input = sum(r.get("input_tokens", 0) for r in results)
            total_output = sum(r.get("output_tokens", 0) for r in results)

            await save_output(job_id, full_text)

            job = await get_job(job_id)
            if job:
                job['status'] = 'completed'
                job['progress'] = 100
                job['completed_at'] = datetime.now().isoformat()
                job['total_input_tokens'] = total_input
                job['total_output_tokens'] = total_output
                await save_job(job)
                await update_batch_progress(job['batch_id'])

            await delete_pdf(job_id)

        except asyncio.CancelledError:
            job = await get_job(job_id)
            if job:
                job['status'] = 'pending'
                await save_job(job)
            raise

        except Exception as e:
            job = await get_job(job_id)
            if job:
                job['status'] = 'failed'
                job['error'] = str(e)
                await save_job(job)
                await update_batch_progress(job['batch_id'])


async def update_batch_progress(batch_id: str):
    """Update batch completion count."""
    if not batch_id:
        return

    batch = await get_batch(batch_id)
    if not batch:
        return

    jobs = await get_batch_jobs(batch_id)
    completed = sum(1 for j in jobs if j['status'] in ('completed', 'failed'))

    batch['completed_files'] = completed
    if completed >= batch['total_files']:
        batch['status'] = 'completed'

    await save_batch(batch)


async def resume_pending_jobs():
    """Resume jobs that were interrupted."""
    await asyncio.sleep(1)

    try:
        fs = get_firestore()
        docs = await fs.collection(JOBS_COLLECTION).where(
            'status', 'in', ['queued', 'pending', 'processing']
        ).get()

        for doc in docs:
            job = doc.to_dict()
            job_id = job['id']
            if job_id not in active_tasks:
                start_job_processing(job_id)
    except Exception as e:
        print(f"Error resuming jobs: {e}")


def start_job_processing(job_id: str):
    """Start processing a job in the background."""
    if job_id not in active_tasks:
        task = asyncio.create_task(process_job(job_id))
        active_tasks[job_id] = task

        def cleanup(t):
            active_tasks.pop(job_id, None)
        task.add_done_callback(cleanup)


# ============================================
# API Endpoints
# ============================================

@app.post("/api/batch")
async def create_batch_endpoint(
    name: str = Form(None),
    output_path: str = Form(None)
):
    """Create a new batch for grouping uploads."""
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    batch = {
        "id": batch_id,
        "name": name or f"Batch {batch_id[-6:]}",
        "output_path": output_path,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "total_files": 0,
        "completed_files": 0
    }

    await save_batch(batch)
    return {"batch_id": batch_id}


@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    batch_id: str = Form(None),
    relative_path: str = Form(None)
):
    """Upload and queue a PDF for processing."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")

    pdf_bytes = await file.read()
    job_id = f"job_{uuid.uuid4().hex[:12]}"

    await store_pdf(job_id, pdf_bytes)

    if not batch_id:
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        new_batch = {
            "id": batch_id,
            "name": file.filename,
            "output_path": None,
            "created_at": datetime.now().isoformat(),
            "status": "processing",
            "total_files": 1,
            "completed_files": 0
        }
        await save_batch(new_batch)
    else:
        existing_batch = await get_batch(batch_id)
        if existing_batch:
            existing_batch['total_files'] = existing_batch.get('total_files', 0) + 1
            existing_batch['status'] = 'processing'
            await save_batch(existing_batch)

    job = {
        "id": job_id,
        "batch_id": batch_id,
        "filename": file.filename,
        "relative_path": relative_path,
        "status": "queued",
        "progress": 0,
        "total_pages": 0,
        "current_page": 0,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "total_input_tokens": 0,
        "total_output_tokens": 0
    }
    await save_job(job)

    start_job_processing(job_id)

    return {"job_id": job_id, "batch_id": batch_id}


@app.post("/api/upload-multiple")
async def upload_multiple(
    files: List[UploadFile] = File(...),
    batch_name: str = Form(None),
    output_path: str = Form(None),
    relative_paths: str = Form(None)
):
    """Upload multiple PDFs at once."""
    if not files:
        raise HTTPException(400, "No files provided")

    rel_paths = []
    if relative_paths:
        try:
            rel_paths = json.loads(relative_paths)
        except json.JSONDecodeError:
            rel_paths = []

    pdf_files = [f for f in files if f.filename.lower().endswith('.pdf')]

    if not pdf_files:
        raise HTTPException(400, "No PDF files provided")

    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    batch = {
        "id": batch_id,
        "name": batch_name or f"Batch of {len(pdf_files)} files",
        "output_path": output_path,
        "created_at": datetime.now().isoformat(),
        "status": "processing",
        "total_files": len(pdf_files),
        "completed_files": 0
    }
    await save_batch(batch)

    job_ids = []

    for i, file in enumerate(pdf_files):
        pdf_bytes = await file.read()
        job_id = f"job_{uuid.uuid4().hex[:12]}"

        rel_path = rel_paths[i] if i < len(rel_paths) else None

        await store_pdf(job_id, pdf_bytes)

        job = {
            "id": job_id,
            "batch_id": batch_id,
            "filename": file.filename,
            "relative_path": rel_path,
            "status": "queued",
            "progress": 0,
            "total_pages": 0,
            "current_page": 0,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "total_input_tokens": 0,
            "total_output_tokens": 0
        }
        await save_job(job)

        job_ids.append(job_id)
        start_job_processing(job_id)

    return {"batch_id": batch_id, "job_ids": job_ids}


@app.patch("/api/batch/{batch_id}")
async def update_batch_endpoint(
    batch_id: str,
    output_path: str = Form(None),
    name: str = Form(None)
):
    """Update batch settings."""
    batch = await get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    if output_path is not None:
        batch['output_path'] = output_path
    if name is not None:
        batch['name'] = name

    await save_batch(batch)
    return {"status": "updated"}


@app.get("/api/batch/{batch_id}")
async def get_batch_endpoint(batch_id: str):
    """Get batch details with all jobs."""
    batch = await get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    jobs = await get_batch_jobs(batch_id)
    batch["jobs"] = jobs

    return batch


@app.get("/api/batches")
async def list_batches_endpoint():
    """List all batches."""
    return await list_batches()


@app.get("/api/jobs/{job_id}")
async def get_job_endpoint(job_id: str):
    """Get job status and details."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job["status"] == "completed":
        job["pages"] = await get_pages(job_id)

    return job


@app.get("/api/jobs/{job_id}/output")
async def get_job_output(job_id: str):
    """Get the markdown output for a completed job."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job["status"] != "completed":
        raise HTTPException(400, "Job not completed")

    output = await get_output(job_id)

    if not output:
        pages = await get_pages(job_id)
        output = "\n\n---\n\n".join(
            f"## Page {p['page_num']}\n\n{p['text']}" if not p.get('error')
            else f"## Page {p['page_num']}\n\n[Error: {p['error']}]"
            for p in pages
        )

    return {"filename": job["filename"], "text": output}


@app.delete("/api/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    """Delete a job."""
    if job_id in active_tasks:
        active_tasks[job_id].cancel()

    await delete_job_doc(job_id)
    return {"status": "deleted"}


@app.delete("/api/batch/{batch_id}")
async def delete_batch_endpoint(batch_id: str):
    """Delete a batch and all its jobs."""
    jobs = await get_batch_jobs(batch_id)

    for job in jobs:
        job_id = job['id']
        if job_id in active_tasks:
            active_tasks[job_id].cancel()
        await delete_job_doc(job_id)

    await delete_batch_doc(batch_id)

    return {"status": "deleted"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        fs = get_firestore()
        await fs.collection(BATCHES_COLLECTION).limit(1).get()
        firestore_status = "connected"
    except Exception:
        firestore_status = "disconnected"

    return {
        "status": "healthy",
        "service": "olmocr-batch-v2",
        "firestore": firestore_status
    }


# ============================================
# Frontend
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>olmOCR Batch Processor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>
    <style>
        .dropzone { transition: all 0.3s ease; }
        .dropzone.dragover { border-color: #3b82f6; background-color: #eff6ff; }
        .prose { max-width: none; }
        .prose pre {
            background: #1f2937;
            color: #e5e7eb;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
        }
        .prose code {
            background: #e5e7eb;
            padding: 0.2rem 0.4rem;
            border-radius: 0.25rem;
        }
        .prose pre code { background: transparent; padding: 0; }
        .file-tree { font-family: monospace; font-size: 0.875rem; }
        .file-tree-item { padding: 0.25rem 0; }
        .spinner { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .status-pending { background-color: #fef3c7; color: #92400e; }
        .status-processing { background-color: #dbeafe; color: #1e40af; }
        .status-completed { background-color: #d1fae5; color: #065f46; }
        .status-failed { background-color: #fee2e2; color: #991b1b; }
        .status-queued { background-color: #e5e7eb; color: #374151; }
        .dot-pending { background-color: #f59e0b; }
        .dot-processing { background-color: #3b82f6; }
        .dot-completed { background-color: #10b981; }
        .dot-failed { background-color: #ef4444; }
        .dot-queued { background-color: #6b7280; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">
                olmOCR Batch Processor
            </h1>
            <p class="text-gray-600">
                High-performance PDF to Markdown - Upload files or folders
            </p>
            <p class="text-sm text-green-600 mt-2">
                Jobs persist even if you close this page
            </p>
        </div>

        <div class="bg-white rounded-xl shadow-lg p-6 mb-8">
            <div class="flex border-b border-gray-200 mb-6">
                <button onclick="setUploadMode('files')" id="modeFiles"
                    class="px-6 py-3 border-b-2 border-blue-500 text-blue-600 font-medium">
                    Upload Files
                </button>
                <button onclick="setUploadMode('folder')" id="modeFolder"
                    class="px-6 py-3 text-gray-500 hover:text-gray-700 font-medium">
                    Upload Folder
                </button>
            </div>

            <div class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Batch Name (optional)
                </label>
                <input type="text" id="batchName"
                    placeholder="Name for this batch of files"
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent">

                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Output Folder Path (optional)
                </label>
                <div class="flex gap-4">
                    <input type="text" id="outputPath"
                        placeholder="e.g., /documents/ocr-output or C:\\Documents\\Output"
                        class="flex-1 px-4 py-2 border border-gray-300 rounded-lg
                               focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                    <label class="flex items-center gap-2 text-sm text-gray-600">
                        <input type="checkbox" id="preserveStructure" checked
                               class="rounded">
                        Preserve folder structure
                    </label>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                    Note: Output files are downloaded via browser. This path is saved with the batch for reference.
                </p>
            </div>

            <div id="fileUploadArea">
                <div id="dropzone"
                     class="dropzone border-2 border-dashed border-gray-300 rounded-xl
                            p-12 text-center cursor-pointer hover:border-blue-400">
                    <input type="file" id="fileInput" class="hidden"
                           accept=".pdf" multiple>
                    <svg class="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none"
                         viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round"
                              stroke-width="1.5"
                              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5
                                 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                    </svg>
                    <p class="text-xl text-gray-600 mb-2">
                        Drop PDF files here or click to upload
                    </p>
                    <p class="text-sm text-gray-400">
                        Select multiple PDFs to process in parallel
                    </p>
                </div>
            </div>

            <div id="folderUploadArea" class="hidden">
                <div id="folderDropzone"
                     class="dropzone border-2 border-dashed border-gray-300 rounded-xl
                            p-12 text-center cursor-pointer hover:border-blue-400">
                    <input type="file" id="folderInput" class="hidden"
                           webkitdirectory directory multiple>
                    <svg class="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none"
                         viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round"
                              stroke-width="1.5"
                              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2
                                 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                    </svg>
                    <p class="text-xl text-gray-600 mb-2">
                        Click to select a folder
                    </p>
                    <p class="text-sm text-gray-400">
                        All PDFs in the folder and subfolders will be processed
                    </p>
                </div>
            </div>

            <div id="stagedFiles" class="hidden mt-6">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold text-gray-800">
                        Files to Process: <span id="stagedCount">0</span>
                    </h3>
                    <div class="space-x-2">
                        <button onclick="clearStaged()"
                                class="px-4 py-2 bg-gray-200 text-gray-700
                                       rounded-lg hover:bg-gray-300">
                            Clear
                        </button>
                        <button onclick="startProcessing()" id="startBtn"
                                class="px-6 py-2 bg-blue-500 text-white
                                       rounded-lg hover:bg-blue-600 font-medium">
                            Start Processing
                        </button>
                    </div>
                </div>
                <div id="stagedList"
                     class="file-tree bg-gray-50 rounded-lg p-4 max-h-60 overflow-y-auto">
                </div>
            </div>
        </div>

        <div id="batchesSection" class="space-y-4 mb-8"></div>

        <div id="outputSection" class="hidden">
            <div class="bg-white rounded-xl shadow-lg overflow-hidden">
                <div class="border-b border-gray-200 p-4
                            flex justify-between items-center">
                    <h2 id="outputTitle"
                        class="text-xl font-semibold text-gray-800">Output</h2>
                    <div class="space-x-2">
                        <button onclick="copyOutput()"
                                class="px-4 py-2 bg-gray-100 text-gray-700
                                       rounded-lg hover:bg-gray-200 transition">
                            Copy
                        </button>
                        <button onclick="downloadOutput()"
                                class="px-4 py-2 bg-blue-500 text-white
                                       rounded-lg hover:bg-blue-600 transition">
                            Download .md
                        </button>
                    </div>
                </div>
                <div class="p-6">
                    <div class="flex border-b border-gray-200 mb-4">
                        <button onclick="showTab('rendered')" id="tabRendered"
                                class="px-4 py-2 border-b-2 border-blue-500
                                       text-blue-600 font-medium">
                            Rendered
                        </button>
                        <button onclick="showTab('raw')" id="tabRaw"
                                class="px-4 py-2 text-gray-500 hover:text-gray-700">
                            Raw Markdown
                        </button>
                    </div>
                    <div id="renderedOutput" class="prose prose-lg max-w-none"></div>
                    <div id="rawOutput" class="hidden">
                        <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg
                                    overflow-x-auto whitespace-pre-wrap text-sm"></pre>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentOutput = '';
        let currentFilename = '';
        let uploadMode = 'files';
        let stagedFiles = [];
        let activeBatches = {};
        let pollIntervals = {};

        function setUploadMode(mode) {
            uploadMode = mode;
            const filesBtn = document.getElementById('modeFiles');
            const folderBtn = document.getElementById('modeFolder');

            filesBtn.classList.toggle('border-b-2', mode === 'files');
            filesBtn.classList.toggle('border-blue-500', mode === 'files');
            filesBtn.classList.toggle('text-blue-600', mode === 'files');
            filesBtn.classList.toggle('text-gray-500', mode !== 'files');

            folderBtn.classList.toggle('border-b-2', mode === 'folder');
            folderBtn.classList.toggle('border-blue-500', mode === 'folder');
            folderBtn.classList.toggle('text-blue-600', mode === 'folder');
            folderBtn.classList.toggle('text-gray-500', mode !== 'folder');

            document.getElementById('fileUploadArea')
                .classList.toggle('hidden', mode !== 'files');
            document.getElementById('folderUploadArea')
                .classList.toggle('hidden', mode !== 'folder');

            clearStaged();
        }

        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');

        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        dropzone.addEventListener('drop', async (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            // Handle dropped items - check for folders
            const items = e.dataTransfer.items;
            if (items && items.length > 0) {
                await handleDroppedItems(items);
            } else {
                handleFiles(e.dataTransfer.files);
            }
        });
        fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

        const folderDropzone = document.getElementById('folderDropzone');
        const folderInput = document.getElementById('folderInput');

        folderDropzone.addEventListener('click', () => folderInput.click());
        folderDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            folderDropzone.classList.add('dragover');
        });
        folderDropzone.addEventListener('dragleave', () => {
            folderDropzone.classList.remove('dragover');
        });
        folderDropzone.addEventListener('drop', async (e) => {
            e.preventDefault();
            folderDropzone.classList.remove('dragover');
            const items = e.dataTransfer.items;
            if (items && items.length > 0) {
                await handleDroppedItems(items);
            }
        });
        folderInput.addEventListener('change', (e) => handleFolderFiles(e.target.files));

        // Recursively traverse dropped folder items
        async function handleDroppedItems(items) {
            const files = [];

            async function traverseEntry(entry, path = '') {
                if (entry.isFile) {
                    return new Promise((resolve) => {
                        entry.file((file) => {
                            if (file.name.toLowerCase().endsWith('.pdf')) {
                                files.push({
                                    file: file,
                                    relativePath: path + file.name,
                                    name: file.name
                                });
                            }
                            resolve();
                        });
                    });
                } else if (entry.isDirectory) {
                    const reader = entry.createReader();
                    return new Promise((resolve) => {
                        const readEntries = () => {
                            reader.readEntries(async (entries) => {
                                if (entries.length === 0) {
                                    resolve();
                                } else {
                                    for (const e of entries) {
                                        await traverseEntry(e, path + entry.name + '/');
                                    }
                                    readEntries(); // Continue reading (may have more entries)
                                }
                            });
                        };
                        readEntries();
                    });
                }
            }

            for (const item of items) {
                const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
                if (entry) {
                    await traverseEntry(entry);
                } else if (item.kind === 'file') {
                    const file = item.getAsFile();
                    if (file && file.name.toLowerCase().endsWith('.pdf')) {
                        files.push({
                            file: file,
                            relativePath: null,
                            name: file.name
                        });
                    }
                }
            }

            stagedFiles = stagedFiles.concat(files);
            updateStagedDisplay();
        }

        function handleFiles(files) {
            for (const file of files) {
                if (file.name.toLowerCase().endsWith('.pdf')) {
                    stagedFiles.push({
                        file: file,
                        relativePath: null,
                        name: file.name
                    });
                }
            }
            updateStagedDisplay();
        }

        function handleFolderFiles(files) {
            for (const file of files) {
                if (file.name.toLowerCase().endsWith('.pdf')) {
                    const relativePath = file.webkitRelativePath || file.name;
                    stagedFiles.push({
                        file: file,
                        relativePath: relativePath,
                        name: file.name
                    });
                }
            }
            updateStagedDisplay();
        }

        function updateStagedDisplay() {
            const container = document.getElementById('stagedFiles');
            const list = document.getElementById('stagedList');
            const count = document.getElementById('stagedCount');

            if (stagedFiles.length === 0) {
                container.classList.add('hidden');
                return;
            }

            container.classList.remove('hidden');
            count.textContent = stagedFiles.length;

            const byFolder = {};
            stagedFiles.forEach((item, idx) => {
                const path = item.relativePath || '';
                const parts = path.split('/');
                const folder = parts.length > 1
                    ? parts.slice(0, -1).join('/')
                    : '(root)';
                if (!byFolder[folder]) byFolder[folder] = [];
                byFolder[folder].push({ ...item, idx });
            });

            // Sort folders alphabetically
            const sortedFolders = Object.keys(byFolder).sort((a, b) => {
                if (a === '(root)') return -1;
                if (b === '(root)') return 1;
                return a.localeCompare(b);
            });

            let html = '';
            for (const folder of sortedFolders) {
                const files = byFolder[folder];
                if (folder !== '(root)') {
                    html += `<div class="font-bold text-gray-700 mt-2">
                        &#128193; ${folder}/</div>`;
                }
                for (const f of files) {
                    html += `<div class="file-tree-item flex justify-between
                                         items-center pl-4">
                        <span>&#128196; ${f.name}</span>
                        <button onclick="removeStaged(${f.idx})"
                                class="text-red-500 hover:text-red-700 text-sm px-2">
                            &times;
                        </button>
                    </div>`;
                }
            }
            list.innerHTML = html;
        }

        function removeStaged(idx) {
            stagedFiles.splice(idx, 1);
            updateStagedDisplay();
        }

        function clearStaged() {
            stagedFiles = [];
            updateStagedDisplay();
            fileInput.value = '';
            folderInput.value = '';
        }

        async function startProcessing() {
            if (stagedFiles.length === 0) return;

            const startBtn = document.getElementById('startBtn');
            startBtn.disabled = true;
            startBtn.textContent = 'Uploading...';

            const outputPath = document.getElementById('outputPath').value.trim();
            const batchNameInput = document.getElementById('batchName').value.trim();
            const preserveStructure = document.getElementById('preserveStructure').checked;

            const formData = new FormData();
            const relativePaths = [];

            for (const item of stagedFiles) {
                formData.append('files', item.file);
                if (preserveStructure && item.relativePath) {
                    relativePaths.push(item.relativePath);
                } else {
                    relativePaths.push(null);
                }
            }

            formData.append('relative_paths', JSON.stringify(relativePaths));
            if (outputPath) {
                formData.append('output_path', outputPath);
            }

            let batchName = batchNameInput;
            if (!batchName) {
                batchName = uploadMode === 'folder'
                    ? `Folder: ${stagedFiles[0]?.relativePath?.split('/')[0] || 'Upload'}`
                    : `${stagedFiles.length} file${stagedFiles.length > 1 ? 's' : ''}`;
            }
            formData.append('batch_name', batchName);

            try {
                const response = await fetch('/api/upload-multiple', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (response.ok) {
                    pollBatch(data.batch_id);
                    clearStaged();
                    document.getElementById('batchName').value = '';
                } else {
                    alert('Upload failed: ' + (data.detail || 'Unknown error'));
                }

            } catch (error) {
                console.error('Upload failed:', error);
                alert('Upload failed: ' + error.message);
            } finally {
                startBtn.disabled = false;
                startBtn.textContent = 'Start Processing';
            }
        }

        async function pollBatch(batchId) {
            const poll = async () => {
                try {
                    const response = await fetch(`/api/batch/${batchId}`);
                    if (!response.ok) {
                        console.error('Failed to fetch batch:', response.status);
                        return;
                    }
                    const batch = await response.json();
                    activeBatches[batchId] = batch;
                    renderBatches();

                    if (batch.status === 'processing' || batch.status === 'pending') {
                        pollIntervals[batchId] = setTimeout(poll, 1500);
                    }
                } catch (error) {
                    console.error('Poll failed:', error);
                    // Retry after delay on error
                    pollIntervals[batchId] = setTimeout(poll, 3000);
                }
            };
            poll();
        }

        function getStatusClass(status) {
            return `status-${status}`;
        }

        function getDotClass(status) {
            return `dot-${status}`;
        }

        function renderBatches() {
            const container = document.getElementById('batchesSection');

            const batchList = Object.values(activeBatches).sort((a, b) =>
                new Date(b.created_at) - new Date(a.created_at)
            );

            if (batchList.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        No batches yet. Upload some PDFs to get started!
                    </div>
                `;
                return;
            }

            container.innerHTML = batchList.map(batch => {
                const jobs = batch.jobs || [];
                const completedJobs = jobs.filter(j => j.status === 'completed').length;
                const failedJobs = jobs.filter(j => j.status === 'failed').length;
                const processingJobs = jobs.filter(j => j.status === 'processing').length;
                const queuedJobs = jobs.filter(j => j.status === 'queued' || j.status === 'pending').length;

                const overallProgress = batch.total_files > 0
                    ? Math.round((batch.completed_files / batch.total_files) * 100)
                    : 0;

                const canDownloadAll = completedJobs > 0;

                return `
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex-1">
                            <h3 class="text-lg font-semibold text-gray-800">
                                ${batch.name || 'Batch'}
                            </h3>
                            <div class="flex flex-wrap gap-2 mt-1 text-sm">
                                ${completedJobs > 0 ? `<span class="text-green-600">${completedJobs} completed</span>` : ''}
                                ${processingJobs > 0 ? `<span class="text-blue-600">${processingJobs} processing</span>` : ''}
                                ${queuedJobs > 0 ? `<span class="text-gray-500">${queuedJobs} queued</span>` : ''}
                                ${failedJobs > 0 ? `<span class="text-red-500">${failedJobs} failed</span>` : ''}
                            </div>
                            ${batch.output_path ?
                                `<p class="text-xs text-gray-400 mt-1">
                                    Output path: ${batch.output_path}</p>` : ''}
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="px-3 py-1 rounded-full text-sm font-medium ${getStatusClass(batch.status)}">
                                ${batch.status}
                            </span>
                            ${canDownloadAll ? `
                                <button onclick="downloadAllOutputs('${batch.id}')"
                                        class="px-3 py-1 bg-green-500 text-white rounded-lg
                                               hover:bg-green-600 text-sm font-medium">
                                    Download All
                                </button>
                            ` : ''}
                            <button onclick="deleteBatch('${batch.id}')"
                                    class="text-red-500 hover:text-red-700 text-xl px-2">
                                &times;
                            </button>
                        </div>
                    </div>

                    <div class="mb-4">
                        <div class="flex justify-between text-xs text-gray-500 mb-1">
                            <span>Progress: ${batch.completed_files}/${batch.total_files}</span>
                            <span>${overallProgress}%</span>
                        </div>
                        <div class="bg-gray-200 rounded-full h-2">
                            <div class="bg-blue-500 rounded-full h-2 transition-all duration-300"
                                 style="width: ${overallProgress}%"></div>
                        </div>
                    </div>

                    <div class="space-y-2 max-h-80 overflow-y-auto">
                        ${jobs.length === 0 ? `
                            <div class="text-center text-gray-400 py-4">
                                Loading jobs...
                            </div>
                        ` : jobs.map(job => {
                            return `
                            <div class="flex items-center justify-between py-2 px-3
                                        bg-gray-50 rounded-lg">
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2">
                                        <span class="w-2 h-2 rounded-full ${getDotClass(job.status)}"></span>
                                        <p class="text-sm font-medium text-gray-800 truncate">
                                            ${job.filename}
                                        </p>
                                    </div>
                                    ${job.relative_path ?
                                        `<p class="text-xs text-gray-400 truncate ml-4">
                                            ${job.relative_path}</p>` : ''}
                                    ${job.status === 'processing' ? `
                                        <div class="mt-1 ml-4 flex items-center gap-2">
                                            <div class="flex-1 bg-gray-200 rounded-full h-1.5">
                                                <div class="bg-blue-500 rounded-full h-1.5 transition-all"
                                                     style="width: ${job.progress || 0}%">
                                                </div>
                                            </div>
                                            <span class="text-xs text-gray-500 whitespace-nowrap">
                                                ${job.current_page || 0}/${job.total_pages || '?'} pages
                                            </span>
                                        </div>
                                    ` : ''}
                                    ${job.status === 'failed' && job.error ? `
                                        <p class="text-xs text-red-500 ml-4 mt-1">
                                            Error: ${job.error}
                                        </p>
                                    ` : ''}
                                </div>
                                <div class="flex items-center gap-2 ml-4">
                                    ${job.status === 'completed' ? `
                                        <button onclick="viewOutput('${job.id}')"
                                                class="px-2 py-1 bg-blue-100 text-blue-700
                                                       rounded hover:bg-blue-200 text-sm">
                                            View
                                        </button>
                                        <button onclick="downloadJobOutput('${job.id}', '${job.filename.replace(/'/g, "\\'")}')"
                                                class="px-2 py-1 bg-green-100 text-green-700
                                                       rounded hover:bg-green-200 text-sm">
                                            .md
                                        </button>
                                    ` : ''}
                                    <span class="text-xs text-gray-400 capitalize">
                                        ${job.status}
                                    </span>
                                </div>
                            </div>
                            `;
                        }).join('')}
                    </div>
                </div>
                `;
            }).join('');
        }

        async function viewOutput(jobId) {
            try {
                const response = await fetch(`/api/jobs/${jobId}/output`);
                if (!response.ok) {
                    const err = await response.json();
                    alert('Failed to load output: ' + (err.detail || 'Unknown error'));
                    return;
                }
                const data = await response.json();

                currentOutput = data.text;
                currentFilename = data.filename
                    .replace('.pdf', '.md')
                    .replace('.PDF', '.md');

                document.getElementById('outputSection').classList.remove('hidden');
                document.getElementById('outputTitle').textContent = data.filename;
                document.getElementById('renderedOutput').innerHTML =
                    marked.parse(data.text);
                document.getElementById('rawOutput').querySelector('pre')
                    .textContent = data.text;

                document.getElementById('outputSection')
                    .scrollIntoView({ behavior: 'smooth' });
            } catch (error) {
                console.error('Failed to load output:', error);
                alert('Failed to load output: ' + error.message);
            }
        }

        async function downloadJobOutput(jobId, filename) {
            try {
                const response = await fetch(`/api/jobs/${jobId}/output`);
                if (!response.ok) {
                    alert('Failed to download');
                    return;
                }
                const data = await response.json();

                const mdFilename = filename.replace(/\\.pdf$/i, '.md');
                const blob = new Blob([data.text], { type: 'text/markdown' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = mdFilename;
                a.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                console.error('Download failed:', error);
                alert('Download failed');
            }
        }

        async function downloadAllOutputs(batchId) {
            const batch = activeBatches[batchId];
            if (!batch || !batch.jobs) return;

            const completedJobs = batch.jobs.filter(j => j.status === 'completed');
            if (completedJobs.length === 0) {
                alert('No completed jobs to download');
                return;
            }

            // If only one file, download directly
            if (completedJobs.length === 1) {
                const job = completedJobs[0];
                await downloadJobOutput(job.id, job.filename);
                return;
            }

            // Multiple files - create a zip
            try {
                const zip = new JSZip();

                for (const job of completedJobs) {
                    const response = await fetch(`/api/jobs/${job.id}/output`);
                    if (!response.ok) continue;
                    const data = await response.json();

                    let filepath = job.filename.replace(/\\.pdf$/i, '.md');
                    if (job.relative_path) {
                        filepath = job.relative_path.replace(/\\.pdf$/i, '.md');
                    }

                    zip.file(filepath, data.text);
                }

                const content = await zip.generateAsync({ type: 'blob' });
                const url = URL.createObjectURL(content);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${batch.name || 'batch'}.zip`;
                a.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                console.error('Zip creation failed:', error);
                alert('Failed to create zip file');
            }
        }

        async function deleteBatch(batchId) {
            if (!confirm('Delete this batch and all its jobs?')) return;

            if (pollIntervals[batchId]) {
                clearTimeout(pollIntervals[batchId]);
                delete pollIntervals[batchId];
            }

            try {
                await fetch(`/api/batch/${batchId}`, { method: 'DELETE' });
                delete activeBatches[batchId];
                renderBatches();
            } catch (error) {
                console.error('Delete failed:', error);
            }
        }

        function showTab(tab) {
            const rendered = document.getElementById('renderedOutput');
            const raw = document.getElementById('rawOutput');
            const tabRendered = document.getElementById('tabRendered');
            const tabRaw = document.getElementById('tabRaw');

            if (tab === 'rendered') {
                rendered.classList.remove('hidden');
                raw.classList.add('hidden');
                tabRendered.classList.add('border-b-2', 'border-blue-500',
                                          'text-blue-600');
                tabRaw.classList.remove('border-b-2', 'border-blue-500',
                                        'text-blue-600');
            } else {
                rendered.classList.add('hidden');
                raw.classList.remove('hidden');
                tabRaw.classList.add('border-b-2', 'border-blue-500',
                                     'text-blue-600');
                tabRendered.classList.remove('border-b-2', 'border-blue-500',
                                             'text-blue-600');
            }
        }

        function copyOutput() {
            navigator.clipboard.writeText(currentOutput);
            alert('Copied to clipboard!');
        }

        function downloadOutput() {
            const blob = new Blob([currentOutput], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = currentFilename;
            a.click();
            URL.revokeObjectURL(url);
        }

        async function loadExistingBatches() {
            try {
                const response = await fetch('/api/batches');
                if (!response.ok) {
                    console.error('Failed to load batches');
                    return;
                }
                const batches = await response.json();

                for (const batch of batches) {
                    if (batch.status === 'processing' || batch.status === 'pending') {
                        pollBatch(batch.id);
                    } else {
                        // Load full batch with jobs
                        const fullResponse = await fetch(`/api/batch/${batch.id}`);
                        if (fullResponse.ok) {
                            activeBatches[batch.id] = await fullResponse.json();
                        }
                    }
                }
                renderBatches();
            } catch (error) {
                console.error('Failed to load batches:', error);
            }
        }

        // Initialize
        loadExistingBatches();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main page."""
    return HTML_TEMPLATE


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("\n" + "=" * 50)
    print("olmOCR Batch Processor v2.0")
    print("=" * 50)
    print("\nFeatures:")
    print(f"  - Parallel processing ({MAX_CONCURRENT_PAGES} pages concurrent)")
    print("  - Persistent jobs via Firestore")
    print("  - Folder uploads with structure preservation")
    print("  - Configurable output locations")
    print(f"\nGCP Project: {GCP_PROJECT_ID or 'auto-detect'}")
    if GCS_BUCKET:
        print(f"GCS Bucket: {GCS_BUCKET}")
    print(f"\nOpen http://localhost:{port} in your browser")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=port)
