#!/usr/bin/env python3
"""
olmOCR Simple Batch Processor

A simple web app for batch processing PDFs using olmOCR via Parasail API.
No document limitations - process as many PDFs as you want.

Usage:
    pip install -r requirements.txt
    python app.py

Then open http://localhost:8000 in your browser.
"""

import asyncio
import base64
import io
import json
import os
import tempfile
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import aiohttp
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pdf2image import convert_from_bytes
from PIL import Image

# ============================================
# Configuration
# ============================================

PARASAIL_API_KEY = os.environ.get("PARASAIL_API_KEY", "psk-aimiwsstmt1A-JBSW3y4jAxHjEvwMvScP")
PARASAIL_API_URL = "https://api.parasail.io/v1/chat/completions"
PARASAIL_MODEL = "allenai/olmOCR-2-7B-1025"

# ============================================
# App Setup
# ============================================

app = FastAPI(title="olmOCR Batch Processor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store processing jobs
jobs = {}

# ============================================
# olmOCR Processing
# ============================================

def get_ocr_prompt():
    """Get the olmOCR prompt."""
    return """Below is the image of one page of a document. Just return the plain text representation of this document as if you were reading it naturally.
Do not hallucinate.

Return the text in markdown format."""


async def render_page_to_base64(pdf_bytes: bytes, page_num: int, dpi: int = 150) -> str:
    """Render a PDF page to base64 PNG."""
    loop = asyncio.get_event_loop()

    def _render():
        images = convert_from_bytes(pdf_bytes, dpi=dpi, first_page=page_num + 1, last_page=page_num + 1)
        if not images:
            raise ValueError(f"Could not render page {page_num}")

        img = images[0]

        # Resize if too large
        max_dim = 1568
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        return base64.b64encode(buffer.getvalue()).decode()

    return await loop.run_in_executor(None, _render)


async def process_page(session: aiohttp.ClientSession, image_base64: str, page_num: int) -> dict:
    """Process a single page via Parasail API."""

    payload = {
        "model": PARASAIL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": get_ocr_prompt()},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
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

    async with session.post(PARASAIL_API_URL, json=payload, headers=headers) as response:
        if response.status != 200:
            error = await response.text()
            raise Exception(f"API error: {error}")

        result = await response.json()
        text = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})

        return {
            "page": page_num + 1,
            "text": text,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0)
        }


async def process_pdf(job_id: str, pdf_bytes: bytes, filename: str):
    """Process a PDF document."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["started_at"] = datetime.now().isoformat()

        # Get page count
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)

        jobs[job_id]["total_pages"] = num_pages
        jobs[job_id]["pages"] = []

        async with aiohttp.ClientSession() as session:
            for page_num in range(num_pages):
                try:
                    # Update progress
                    jobs[job_id]["current_page"] = page_num + 1
                    jobs[job_id]["progress"] = int((page_num / num_pages) * 100)

                    # Render page
                    image_base64 = await render_page_to_base64(pdf_bytes, page_num)

                    # Process via API
                    result = await process_page(session, image_base64, page_num)

                    jobs[job_id]["pages"].append(result)

                except Exception as e:
                    jobs[job_id]["pages"].append({
                        "page": page_num + 1,
                        "text": f"[Error processing page: {str(e)}]",
                        "error": True
                    })

        # Combine all pages
        full_text = "\n\n---\n\n".join(
            f"## Page {p['page']}\n\n{p['text']}"
            for p in jobs[job_id]["pages"]
        )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["full_text"] = full_text
        jobs[job_id]["total_input_tokens"] = sum(p.get("input_tokens", 0) for p in jobs[job_id]["pages"])
        jobs[job_id]["total_output_tokens"] = sum(p.get("output_tokens", 0) for p in jobs[job_id]["pages"])

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# ============================================
# API Endpoints
# ============================================

@app.post("/api/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload and process a PDF."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")

    pdf_bytes = await file.read()

    # Create job
    job_id = f"job_{int(time.time() * 1000)}"
    jobs[job_id] = {
        "id": job_id,
        "filename": file.filename,
        "status": "queued",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "total_pages": 0,
        "current_page": 0,
        "pages": []
    }

    # Process in background
    background_tasks.add_task(process_pdf, job_id, pdf_bytes, file.filename)

    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    return list(jobs.values())


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job."""
    if job_id in jobs:
        del jobs[job_id]
    return {"status": "deleted"}


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
    <style>
        .dropzone { transition: all 0.3s ease; }
        .dropzone.dragover { border-color: #3b82f6; background-color: #eff6ff; }
        .prose { max-width: none; }
        .prose pre { background: #1f2937; color: #e5e7eb; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }
        .prose code { background: #e5e7eb; padding: 0.2rem 0.4rem; border-radius: 0.25rem; }
        .prose pre code { background: transparent; padding: 0; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">olmOCR Batch Processor</h1>
            <p class="text-gray-600">Convert PDFs to Markdown using AI - No document limits</p>
        </div>

        <!-- Upload Area -->
        <div id="dropzone" class="dropzone border-2 border-dashed border-gray-300 rounded-xl p-12 text-center bg-white mb-8 cursor-pointer hover:border-blue-400">
            <input type="file" id="fileInput" class="hidden" accept=".pdf" multiple>
            <svg class="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
            </svg>
            <p class="text-xl text-gray-600 mb-2">Drop PDF files here or click to upload</p>
            <p class="text-sm text-gray-400">Process multiple PDFs at once - no limits!</p>
        </div>

        <!-- Jobs List -->
        <div id="jobsList" class="space-y-4 mb-8"></div>

        <!-- Output Display -->
        <div id="outputSection" class="hidden">
            <div class="bg-white rounded-xl shadow-lg overflow-hidden">
                <div class="border-b border-gray-200 p-4 flex justify-between items-center">
                    <h2 id="outputTitle" class="text-xl font-semibold text-gray-800">Output</h2>
                    <div class="space-x-2">
                        <button onclick="copyOutput()" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition">
                            Copy
                        </button>
                        <button onclick="downloadOutput()" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
                            Download .md
                        </button>
                    </div>
                </div>
                <div class="p-6">
                    <div class="flex border-b border-gray-200 mb-4">
                        <button onclick="showTab('rendered')" id="tabRendered" class="px-4 py-2 border-b-2 border-blue-500 text-blue-600 font-medium">Rendered</button>
                        <button onclick="showTab('raw')" id="tabRaw" class="px-4 py-2 text-gray-500 hover:text-gray-700">Raw Markdown</button>
                    </div>
                    <div id="renderedOutput" class="prose prose-lg max-w-none"></div>
                    <div id="rawOutput" class="hidden">
                        <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto whitespace-pre-wrap text-sm"></pre>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentOutput = '';
        let currentFilename = '';

        // Dropzone handling
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
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

        async function handleFiles(files) {
            for (const file of files) {
                if (file.type === 'application/pdf') {
                    await uploadFile(file);
                }
            }
        }

        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                pollJob(data.job_id);
            } catch (error) {
                console.error('Upload failed:', error);
                alert('Upload failed: ' + error.message);
            }
        }

        async function pollJob(jobId) {
            const poll = async () => {
                try {
                    const response = await fetch(`/api/jobs/${jobId}`);
                    const job = await response.json();
                    renderJob(job);

                    if (job.status === 'processing' || job.status === 'queued') {
                        setTimeout(poll, 1000);
                    } else if (job.status === 'completed') {
                        showOutput(job);
                    }
                } catch (error) {
                    console.error('Poll failed:', error);
                }
            };
            poll();
        }

        function renderJob(job) {
            const jobsList = document.getElementById('jobsList');
            let jobEl = document.getElementById(`job-${job.id}`);

            if (!jobEl) {
                jobEl = document.createElement('div');
                jobEl.id = `job-${job.id}`;
                jobEl.className = 'bg-white rounded-xl shadow p-4';
                jobsList.prepend(jobEl);
            }

            const statusColors = {
                queued: 'bg-yellow-100 text-yellow-800',
                processing: 'bg-blue-100 text-blue-800',
                completed: 'bg-green-100 text-green-800',
                failed: 'bg-red-100 text-red-800'
            };

            jobEl.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-4">
                        <div>
                            <p class="font-medium text-gray-800">${job.filename}</p>
                            <p class="text-sm text-gray-500">
                                ${job.status === 'processing' ? `Page ${job.current_page} of ${job.total_pages}` :
                                  job.status === 'completed' ? `${job.total_pages} pages processed` :
                                  job.status}
                            </p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-4">
                        <span class="px-3 py-1 rounded-full text-sm font-medium ${statusColors[job.status]}">${job.status}</span>
                        ${job.status === 'completed' ? `
                            <button onclick="showOutput(${JSON.stringify(job).replace(/"/g, '&quot;')})" class="text-blue-500 hover:text-blue-700">View Output</button>
                        ` : ''}
                        <button onclick="deleteJob('${job.id}')" class="text-red-500 hover:text-red-700">×</button>
                    </div>
                </div>
                ${job.status === 'processing' ? `
                    <div class="mt-3">
                        <div class="bg-gray-200 rounded-full h-2">
                            <div class="bg-blue-500 rounded-full h-2 transition-all" style="width: ${job.progress}%"></div>
                        </div>
                    </div>
                ` : ''}
            `;
        }

        function showOutput(job) {
            currentOutput = job.full_text;
            currentFilename = job.filename.replace('.pdf', '.md');

            document.getElementById('outputSection').classList.remove('hidden');
            document.getElementById('outputTitle').textContent = job.filename;
            document.getElementById('renderedOutput').innerHTML = marked.parse(job.full_text);
            document.getElementById('rawOutput').querySelector('pre').textContent = job.full_text;

            document.getElementById('outputSection').scrollIntoView({ behavior: 'smooth' });
        }

        function showTab(tab) {
            if (tab === 'rendered') {
                document.getElementById('renderedOutput').classList.remove('hidden');
                document.getElementById('rawOutput').classList.add('hidden');
                document.getElementById('tabRendered').classList.add('border-b-2', 'border-blue-500', 'text-blue-600');
                document.getElementById('tabRaw').classList.remove('border-b-2', 'border-blue-500', 'text-blue-600');
            } else {
                document.getElementById('renderedOutput').classList.add('hidden');
                document.getElementById('rawOutput').classList.remove('hidden');
                document.getElementById('tabRaw').classList.add('border-b-2', 'border-blue-500', 'text-blue-600');
                document.getElementById('tabRendered').classList.remove('border-b-2', 'border-blue-500', 'text-blue-600');
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

        async function deleteJob(jobId) {
            await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
            const jobEl = document.getElementById(`job-${jobId}`);
            if (jobEl) jobEl.remove();
        }
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
    print("olmOCR Batch Processor")
    print("=" * 50)
    print(f"\nOpen http://localhost:{port} in your browser")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=port)
