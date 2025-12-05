#!/usr/bin/env python3
"""
olmOCR Batch Processor v3.0

A simple, high-performance web app for batch processing PDFs using olmOCR.

FEATURES:
- Works locally without any cloud services (SQLite storage)
- Optional cloud mode with Google Cloud Firestore/Storage
- Parallel page processing (5-10x faster than sequential)
- Persistent jobs (survive page refresh/browser close)
- Folder uploads with structure preservation
- Beautiful responsive web UI

QUICK START (Local Mode - No Cloud Required):
    pip install -r requirements.txt
    export PARASAIL_API_KEY="your-key"   # Get from https://parasail.io
    python app.py

Then open http://localhost:8080 in your browser.

STORAGE MODES:
- Local (default): Uses SQLite + filesystem - no cloud services needed
- Cloud: Uses Google Cloud Firestore + GCS (set GCP_PROJECT_ID)
"""

import asyncio
import base64
import io
import json
import os
import sqlite3
import uuid
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import threading

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # Loads from .env in current directory or parent directories

import aiohttp
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pdf2image import convert_from_bytes
from PIL import Image

# ============================================
# Configuration
# ============================================

# Parasail API Configuration
PARASAIL_API_KEY = os.environ.get("PARASAIL_API_KEY", "")
PARASAIL_API_URL = os.environ.get("PARASAIL_API_URL", "https://api.parasail.io/v1/chat/completions")
PARASAIL_MODEL = os.environ.get("PARASAIL_MODEL", "allenai/olmOCR-2-7B-1025")

# Performance settings
MAX_CONCURRENT_PAGES = int(os.environ.get("MAX_CONCURRENT_PAGES", "5"))
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", "3"))
RENDER_DPI = int(os.environ.get("RENDER_DPI", "120"))
IMAGE_QUALITY = int(os.environ.get("IMAGE_QUALITY", "85"))

# Storage mode: "local" (SQLite + filesystem) or "cloud" (Firestore + GCS)
STORAGE_MODE = os.environ.get("STORAGE_MODE", "local")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "")

# Firestore collection names
BATCHES_COLLECTION = "ocr_batches"
JOBS_COLLECTION = "ocr_jobs"
PAGES_COLLECTION = "ocr_pages"
SETTINGS_COLLECTION = "ocr_settings"
SETTINGS_DOC_ID = "app_config"
# Local storage paths
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DB_PATH = DATA_DIR / "olmocr.db"
PDF_DIR = DATA_DIR / "pdfs"
OUTPUT_DIR = DATA_DIR / "outputs"

# ============================================
# Storage Backend Interface
# ============================================

class StorageBackend:
    """Abstract storage backend interface."""

    async def init(self):
        raise NotImplementedError

    async def save_batch(self, batch: dict):
        raise NotImplementedError

    async def get_batch(self, batch_id: str) -> Optional[dict]:
        raise NotImplementedError

    async def delete_batch(self, batch_id: str):
        raise NotImplementedError

    async def list_batches(self) -> List[dict]:
        raise NotImplementedError

    async def save_job(self, job: dict):
        raise NotImplementedError

# ============================================
# Settings Management (Web-configurable)
# ============================================

# Cache for settings to avoid repeated Firestore reads
_settings_cache: Dict[str, any] = {}
_settings_cache_time: Optional[datetime] = None
SETTINGS_CACHE_TTL = 300  # 5 minutes


async def get_settings() -> Dict:
    """Get application settings from Firestore."""
    global _settings_cache, _settings_cache_time

    # Check cache
    if _settings_cache and _settings_cache_time:
        age = (datetime.now() - _settings_cache_time).total_seconds()
        if age < SETTINGS_CACHE_TTL:
            return _settings_cache

    try:
        fs = get_firestore()
        doc = await fs.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC_ID).get()
        if doc.exists:
            _settings_cache = doc.to_dict()
            _settings_cache_time = datetime.now()
            return _settings_cache
    except Exception as e:
        print(f"Error reading settings: {e}")

    return {}


async def save_settings(settings: Dict) -> bool:
    """Save application settings to Firestore."""
    global _settings_cache, _settings_cache_time

    try:
        fs = get_firestore()
        settings['updated_at'] = datetime.now().isoformat()
        await fs.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC_ID).set(settings, merge=True)

        # Update cache
        _settings_cache = {**_settings_cache, **settings}
        _settings_cache_time = datetime.now()
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


async def get_api_key() -> str:
    """Get Parasail API key - checks Firestore first, falls back to env var."""
    settings = await get_settings()
    api_key = settings.get('parasail_api_key', '')

    # Fall back to environment variable if not in Firestore
    if not api_key:
        api_key = PARASAIL_API_KEY

    return api_key


async def is_configured() -> bool:
    """Check if the app has been configured with an API key."""
    api_key = await get_api_key()
    return bool(api_key and len(api_key) > 10)


def clear_settings_cache():
    """Clear the settings cache to force a refresh."""
    global _settings_cache, _settings_cache_time
    _settings_cache = {}
    _settings_cache_time = None


# ============================================
# App Setup
# ============================================
    async def get_job(self, job_id: str) -> Optional[dict]:
        raise NotImplementedError

    async def delete_job(self, job_id: str):
        raise NotImplementedError

    async def get_batch_jobs(self, batch_id: str) -> List[dict]:
        raise NotImplementedError

    async def get_pending_jobs(self) -> List[dict]:
        raise NotImplementedError

    async def save_output(self, job_id: str, text: str):
        raise NotImplementedError

    async def get_output(self, job_id: str) -> Optional[str]:
        raise NotImplementedError

    async def store_pdf(self, job_id: str, pdf_bytes: bytes):
        raise NotImplementedError

    async def load_pdf(self, job_id: str) -> Optional[bytes]:
        raise NotImplementedError

    async def delete_pdf(self, job_id: str):
        raise NotImplementedError


# ============================================
# SQLite Local Storage Backend
# ============================================

class SQLiteBackend(StorageBackend):
    """Local storage using SQLite and filesystem."""

    def __init__(self):
        self._local = threading.local()
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    async def init(self):
        """Initialize database and directories."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (batch_id) REFERENCES batches(id)
            );

            CREATE TABLE IF NOT EXISTS outputs (
                job_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_batch ON jobs(batch_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(json_extract(data, '$.status'));
        """)
        conn.commit()
        print(f"SQLite database initialized at {DB_PATH}")

    async def save_batch(self, batch: dict):
        def _save():
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO batches (id, data, created_at) VALUES (?, ?, ?)",
                (batch['id'], json.dumps(batch), batch.get('created_at', datetime.now().isoformat()))
            )
            conn.commit()
        await asyncio.get_event_loop().run_in_executor(self._executor, _save)

    async def get_batch(self, batch_id: str) -> Optional[dict]:
        def _get():
            conn = self._get_conn()
            row = conn.execute("SELECT data FROM batches WHERE id = ?", (batch_id,)).fetchone()
            return json.loads(row['data']) if row else None
        return await asyncio.get_event_loop().run_in_executor(self._executor, _get)

    async def delete_batch(self, batch_id: str):
        def _delete():
            conn = self._get_conn()
            conn.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
            conn.commit()
        await asyncio.get_event_loop().run_in_executor(self._executor, _delete)

    async def list_batches(self) -> List[dict]:
        def _list():
            conn = self._get_conn()
            rows = conn.execute("SELECT data FROM batches ORDER BY created_at DESC").fetchall()
            return [json.loads(row['data']) for row in rows]
        return await asyncio.get_event_loop().run_in_executor(self._executor, _list)

    async def save_job(self, job: dict):
        def _save():
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO jobs (id, batch_id, data, created_at) VALUES (?, ?, ?, ?)",
                (job['id'], job['batch_id'], json.dumps(job), job.get('created_at', datetime.now().isoformat()))
            )
            conn.commit()
        await asyncio.get_event_loop().run_in_executor(self._executor, _save)

    async def get_job(self, job_id: str) -> Optional[dict]:
        def _get():
            conn = self._get_conn()
            row = conn.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return json.loads(row['data']) if row else None
        return await asyncio.get_event_loop().run_in_executor(self._executor, _get)

    async def delete_job(self, job_id: str):
        def _delete():
            conn = self._get_conn()
            conn.execute("DELETE FROM outputs WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
        await asyncio.get_event_loop().run_in_executor(self._executor, _delete)
        await self.delete_pdf(job_id)

    async def get_batch_jobs(self, batch_id: str) -> List[dict]:
        def _get():
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT data FROM jobs WHERE batch_id = ? ORDER BY created_at",
                (batch_id,)
            ).fetchall()
            return [json.loads(row['data']) for row in rows]
        return await asyncio.get_event_loop().run_in_executor(self._executor, _get)

    async def get_pending_jobs(self) -> List[dict]:
        def _get():
            conn = self._get_conn()
            rows = conn.execute("""
                SELECT data FROM jobs
                WHERE json_extract(data, '$.status') IN ('queued', 'pending', 'processing')
            """).fetchall()
            return [json.loads(row['data']) for row in rows]
        return await asyncio.get_event_loop().run_in_executor(self._executor, _get)

    async def save_output(self, job_id: str, text: str):
        def _save():
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO outputs (job_id, text, created_at) VALUES (?, ?, ?)",
                (job_id, text, datetime.now().isoformat())
            )
            conn.commit()
        await asyncio.get_event_loop().run_in_executor(self._executor, _save)

        # Also save to file for easy access
        output_file = OUTPUT_DIR / f"{job_id}.md"
        output_file.write_text(text, encoding='utf-8')

    async def get_output(self, job_id: str) -> Optional[str]:
        def _get():
            conn = self._get_conn()
            row = conn.execute("SELECT text FROM outputs WHERE job_id = ?", (job_id,)).fetchone()
            return row['text'] if row else None
        return await asyncio.get_event_loop().run_in_executor(self._executor, _get)

    async def store_pdf(self, job_id: str, pdf_bytes: bytes):
        def _store():
            pdf_path = PDF_DIR / f"{job_id}.pdf"
            pdf_path.write_bytes(pdf_bytes)
        await asyncio.get_event_loop().run_in_executor(self._executor, _store)

    async def load_pdf(self, job_id: str) -> Optional[bytes]:
        def _load():
            pdf_path = PDF_DIR / f"{job_id}.pdf"
            if pdf_path.exists():
                return pdf_path.read_bytes()
            return None
        return await asyncio.get_event_loop().run_in_executor(self._executor, _load)

    async def delete_pdf(self, job_id: str):
        def _delete():
            pdf_path = PDF_DIR / f"{job_id}.pdf"
            if pdf_path.exists():
                pdf_path.unlink()
        await asyncio.get_event_loop().run_in_executor(self._executor, _delete)


# ============================================
# Firestore Cloud Storage Backend
# ============================================

class FirestoreBackend(StorageBackend):
    """Cloud storage using Google Cloud Firestore and GCS."""

    def __init__(self):
        self.db = None
        self.gcs_client = None
        self._memory_store: Dict[str, bytes] = {}  # Fallback if no GCS

    async def init(self):
        from google.cloud import firestore
        from google.cloud import storage

        if GCP_PROJECT_ID:
            self.db = firestore.AsyncClient(project=GCP_PROJECT_ID)
        else:
            self.db = firestore.AsyncClient()

        if GCS_BUCKET:
            self.gcs_client = storage.Client()

        # Test connection
        await self.db.collection('_health').limit(1).get()
        print(f"Connected to Firestore (project: {GCP_PROJECT_ID or 'auto-detect'})")

    async def save_batch(self, batch: dict):
        await self.db.collection('ocr_batches').document(batch['id']).set(batch)

    async def get_batch(self, batch_id: str) -> Optional[dict]:
        doc = await self.db.collection('ocr_batches').document(batch_id).get()
        return doc.to_dict() if doc.exists else None

    async def delete_batch(self, batch_id: str):
        await self.db.collection('ocr_batches').document(batch_id).delete()

    async def list_batches(self) -> List[dict]:
        docs = await self.db.collection('ocr_batches').get()
        batches = [doc.to_dict() for doc in docs]
        batches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return batches

    async def save_job(self, job: dict):
        await self.db.collection('ocr_jobs').document(job['id']).set(job)

    async def get_job(self, job_id: str) -> Optional[dict]:
        doc = await self.db.collection('ocr_jobs').document(job_id).get()
        return doc.to_dict() if doc.exists else None

    async def delete_job(self, job_id: str):
        await self.db.collection('ocr_jobs').document(job_id).delete()
        await self.delete_pdf(job_id)

    async def get_batch_jobs(self, batch_id: str) -> List[dict]:
        docs = await self.db.collection('ocr_jobs').where('batch_id', '==', batch_id).get()
        jobs = [doc.to_dict() for doc in docs]
        jobs.sort(key=lambda x: x.get('created_at', ''))
        return jobs

    async def get_pending_jobs(self) -> List[dict]:
        docs = await self.db.collection('ocr_jobs').where(
            'status', 'in', ['queued', 'pending', 'processing']
        ).get()
        return [doc.to_dict() for doc in docs]

    async def save_output(self, job_id: str, text: str):
        await self.db.collection('ocr_outputs').document(job_id).set({
            'text': text,
            'created_at': datetime.now().isoformat()
        })

    async def get_output(self, job_id: str) -> Optional[str]:
        doc = await self.db.collection('ocr_outputs').document(job_id).get()
        return doc.to_dict().get('text') if doc.exists else None

    async def store_pdf(self, job_id: str, pdf_bytes: bytes):
        if self.gcs_client and GCS_BUCKET:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.gcs_client.bucket(GCS_BUCKET).blob(f"pdfs/{job_id}.pdf").upload_from_string(
                    pdf_bytes, content_type='application/pdf'
                )
            )
        else:
            self._memory_store[job_id] = pdf_bytes

    async def load_pdf(self, job_id: str) -> Optional[bytes]:
        if self.gcs_client and GCS_BUCKET:
            loop = asyncio.get_event_loop()
            try:
                blob = self.gcs_client.bucket(GCS_BUCKET).blob(f"pdfs/{job_id}.pdf")
                return await loop.run_in_executor(None, blob.download_as_bytes)
            except Exception:
                return None
        else:
            return self._memory_store.get(job_id)

    async def delete_pdf(self, job_id: str):
        if self.gcs_client and GCS_BUCKET:
            loop = asyncio.get_event_loop()
            try:
                blob = self.gcs_client.bucket(GCS_BUCKET).blob(f"pdfs/{job_id}.pdf")
                await loop.run_in_executor(None, blob.delete)
            except Exception:
                pass
        else:
            self._memory_store.pop(job_id, None)


# ============================================
# Global State
# ============================================

storage: StorageBackend = None
active_tasks: Dict[str, asyncio.Task] = {}
job_semaphore: Optional[asyncio.Semaphore] = None


# ============================================
# App Setup
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    global storage, job_semaphore

    # Initialize storage backend
    if STORAGE_MODE == "cloud" or GCP_PROJECT_ID:
        print("Using Cloud storage mode (Firestore + GCS)")
        storage = FirestoreBackend()
    else:
        print("Using Local storage mode (SQLite + filesystem)")
        storage = SQLiteBackend()

    await storage.init()
    job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

    # Resume pending jobs
    asyncio.create_task(resume_pending_jobs())

    yield

    # Shutdown
    for task in active_tasks.values():
        task.cancel()


app = FastAPI(
    title="olmOCR Batch Processor",
    version="3.0.0",
    description="High-performance PDF to Markdown conversion",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# OCR Processing Functions
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
    """Render all PDF pages at once."""
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
    """Convert image to base64 JPEG."""
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode()


async def process_single_page(
    session: aiohttp.ClientSession,
    image_base64: str,
    page_num: int,
    semaphore: asyncio.Semaphore,
    api_key: str
) -> dict:
    """Process a single page via Parasail API."""

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
            "Authorization": f"Bearer {api_key}",
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


async def process_job(job_id: str):
    """Process a single job with parallel page processing."""
    global job_semaphore

    if job_semaphore is None:
        job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

    async with job_semaphore:
        try:
            job = await storage.get_job(job_id)
            if not job:
                return

            # Get API key dynamically from settings
            api_key = await get_api_key()
            if not api_key:
                raise Exception("No API key configured. Please set up your Parasail API key in Settings.")

            job['status'] = 'processing'
            job['started_at'] = datetime.now().isoformat()
            await storage.save_job(job)

            # Load PDF
            pdf_bytes = await storage.load_pdf(job_id)
            if not pdf_bytes:
                raise Exception("PDF file not found")

            # Render pages
            loop = asyncio.get_event_loop()
            images = await loop.run_in_executor(None, render_all_pages, pdf_bytes)
            num_pages = len(images)

            job['total_pages'] = num_pages
            await storage.save_job(job)

            # Convert to base64
            def convert_images(imgs):
                return [image_to_base64(img) for img in imgs]

            base64_images = await loop.run_in_executor(None, convert_images, images)
            del images  # Free memory

            # Process pages in parallel
            page_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
            completed_pages = 0

            async with aiohttp.ClientSession() as session:
                tasks = [
                    process_single_page(session, img_b64, page_num, page_semaphore, api_key)
                    for page_num, img_b64 in enumerate(base64_images)
                ]

                results = []
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    results.append(result)
                    completed_pages += 1

                    # Update progress
                    job = await storage.get_job(job_id)
                    if job:
                        progress = int((completed_pages / num_pages) * 100)
                        job['current_page'] = completed_pages
                        job['progress'] = progress
                        await storage.save_job(job)

            # Sort results by page number
            results.sort(key=lambda x: x["page_num"])

            # Combine results
            full_text = "\n\n---\n\n".join(
                f"## Page {r['page_num']}\n\n{r['text']}" if not r.get('error')
                else f"## Page {r['page_num']}\n\n[Error: {r['error']}]"
                for r in results
            )

            total_input = sum(r.get("input_tokens", 0) for r in results)
            total_output = sum(r.get("output_tokens", 0) for r in results)

            # Save output
            await storage.save_output(job_id, full_text)

            # Update job status
            job = await storage.get_job(job_id)
            if job:
                job['status'] = 'completed'
                job['progress'] = 100
                job['completed_at'] = datetime.now().isoformat()
                job['total_input_tokens'] = total_input
                job['total_output_tokens'] = total_output
                await storage.save_job(job)
                await update_batch_progress(job['batch_id'])

            # Clean up PDF
            await storage.delete_pdf(job_id)

        except asyncio.CancelledError:
            job = await storage.get_job(job_id)
            if job:
                job['status'] = 'pending'
                await storage.save_job(job)
            raise

        except Exception as e:
            job = await storage.get_job(job_id)
            if job:
                job['status'] = 'failed'
                job['error'] = str(e)
                await storage.save_job(job)
                await update_batch_progress(job['batch_id'])


async def update_batch_progress(batch_id: str):
    """Update batch completion count."""
    if not batch_id:
        return

    batch = await storage.get_batch(batch_id)
    if not batch:
        return

    jobs = await storage.get_batch_jobs(batch_id)
    completed = sum(1 for j in jobs if j['status'] in ('completed', 'failed'))

    batch['completed_files'] = completed
    if completed >= batch['total_files']:
        batch['status'] = 'completed'

    await storage.save_batch(batch)


async def resume_pending_jobs():
    """Resume jobs that were interrupted."""
    await asyncio.sleep(1)

    try:
        pending_jobs = await storage.get_pending_jobs()
        for job in pending_jobs:
            job_id = job['id']
            if job_id not in active_tasks:
                start_job_processing(job_id)

        if pending_jobs:
            print(f"Resumed {len(pending_jobs)} pending jobs")
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

@app.get("/api/status")
async def get_status():
    """Get system status and configuration."""
    has_api_key = bool(PARASAIL_API_KEY)

    return {
        "status": "ready" if has_api_key else "needs_configuration",
        "has_api_key": has_api_key,
        "storage_mode": "cloud" if isinstance(storage, FirestoreBackend) else "local",
        "max_concurrent_pages": MAX_CONCURRENT_PAGES,
        "max_concurrent_jobs": MAX_CONCURRENT_JOBS,
        "active_jobs": len(active_tasks),
        "data_directory": str(DATA_DIR) if isinstance(storage, SQLiteBackend) else None
    }


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

    await storage.save_batch(batch)
    return {"batch_id": batch_id}


@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    batch_id: str = Form(None),
    relative_path: str = Form(None)
):
    """Upload and queue a PDF for processing."""
    if not PARASAIL_API_KEY:
        raise HTTPException(400, "PARASAIL_API_KEY not configured. Set it as an environment variable.")

    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(400, "Empty file")

    job_id = f"job_{uuid.uuid4().hex[:12]}"

    await storage.store_pdf(job_id, pdf_bytes)

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
        await storage.save_batch(new_batch)
    else:
        existing_batch = await storage.get_batch(batch_id)
        if existing_batch:
            existing_batch['total_files'] = existing_batch.get('total_files', 0) + 1
            existing_batch['status'] = 'processing'
            await storage.save_batch(existing_batch)

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
    await storage.save_job(job)

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
    if not PARASAIL_API_KEY:
        raise HTTPException(400, "PARASAIL_API_KEY not configured. Set it as an environment variable.")

    if not files:
        raise HTTPException(400, "No files provided")

    rel_paths = []
    if relative_paths:
        try:
            rel_paths = json.loads(relative_paths)
        except json.JSONDecodeError:
            rel_paths = []

    # Filter PDF files
    pdf_files = [f for f in files if f.filename and f.filename.lower().endswith('.pdf')]

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
    await storage.save_batch(batch)

    job_ids = []
    errors = []

    for i, file in enumerate(pdf_files):
        try:
            pdf_bytes = await file.read()

            if not pdf_bytes:
                errors.append(f"{file.filename}: Empty file")
                continue

            job_id = f"job_{uuid.uuid4().hex[:12]}"
            rel_path = rel_paths[i] if i < len(rel_paths) else None

            await storage.store_pdf(job_id, pdf_bytes)

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
            await storage.save_job(job)

            job_ids.append(job_id)
            start_job_processing(job_id)

        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            continue

    # Update batch total if some files failed
    if len(job_ids) < len(pdf_files):
        batch['total_files'] = len(job_ids)
        if len(job_ids) == 0:
            batch['status'] = 'failed'
        await storage.save_batch(batch)

    if not job_ids:
        raise HTTPException(400, f"All uploads failed: {'; '.join(errors)}")

    return {
        "batch_id": batch_id,
        "job_ids": job_ids,
        "errors": errors if errors else None
    }


@app.get("/api/batch/{batch_id}")
async def get_batch_endpoint(batch_id: str):
    """Get batch details with all jobs."""
    batch = await storage.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    jobs = await storage.get_batch_jobs(batch_id)
    batch["jobs"] = jobs

    return batch


@app.get("/api/batches")
async def list_batches_endpoint():
    """List all batches."""
    return await storage.list_batches()


@app.get("/api/jobs/{job_id}")
async def get_job_endpoint(job_id: str):
    """Get job status and details."""
    job = await storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/api/jobs/{job_id}/output")
async def get_job_output(job_id: str):
    """Get the markdown output for a completed job."""
    job = await storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job["status"] != "completed":
        raise HTTPException(400, "Job not completed")

    output = await storage.get_output(job_id)
    if not output:
        raise HTTPException(404, "Output not found")

    return {"filename": job["filename"], "text": output}


@app.delete("/api/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    """Delete a job."""
    if job_id in active_tasks:
        active_tasks[job_id].cancel()

    await storage.delete_job(job_id)
    return {"status": "deleted"}


@app.delete("/api/batch/{batch_id}")
async def delete_batch_endpoint(batch_id: str):
    """Delete a batch and all its jobs."""
    jobs = await storage.get_batch_jobs(batch_id)

    for job in jobs:
        job_id = job['id']
        if job_id in active_tasks:
            active_tasks[job_id].cancel()
        await storage.delete_job(job_id)

    await storage.delete_batch(batch_id)

    return {"status": "deleted"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "olmocr-batch-v3",
        "storage_mode": "cloud" if isinstance(storage, FirestoreBackend) else "local",
        "has_api_key": bool(PARASAIL_API_KEY)
    }


# ============================================
# Frontend HTML
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>olmOCR - PDF to Markdown</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>
    <style>
        .dropzone { transition: all 0.3s ease; }
        .dropzone.dragover { border-color: #3b82f6; background-color: #eff6ff; transform: scale(1.01); }
        .prose { max-width: none; }
        .prose pre { background: #1f2937; color: #e5e7eb; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }
        .prose code { background: #e5e7eb; padding: 0.2rem 0.4rem; border-radius: 0.25rem; font-size: 0.9em; }
        .prose pre code { background: transparent; padding: 0; }
        .prose table { border-collapse: collapse; width: 100%; }
        .prose th, .prose td { border: 1px solid #d1d5db; padding: 0.5rem; }
        .file-tree { font-family: monospace; font-size: 0.875rem; }
        .spinner { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .status-pending { background-color: #fef3c7; color: #92400e; }
        .status-processing { background-color: #dbeafe; color: #1e40af; }
        .status-completed { background-color: #d1fae5; color: #065f46; }
        .status-failed { background-color: #fee2e2; color: #991b1b; }
        .status-queued { background-color: #e5e7eb; color: #374151; }
        .dot-pending { background-color: #f59e0b; }
        .dot-processing { background-color: #3b82f6; animation: pulse 1.5s infinite; }
        .dot-completed { background-color: #10b981; }
        .dot-failed { background-color: #ef4444; }
        .dot-queued { background-color: #6b7280; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .fade-in { animation: fadeIn 0.3s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body class="bg-gradient-to-br from-slate-50 to-blue-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
                olmOCR
            </h1>
            <p class="text-gray-600 text-lg">
                High-performance PDF to Markdown conversion
            </p>
            <div id="statusBadge" class="mt-3"></div>
        </div>

        <!-- API Key Warning -->
        <div id="apiKeyWarning" class="hidden mb-6 bg-yellow-50 border border-yellow-200 rounded-xl p-4">
            <div class="flex items-start gap-3">
                <svg class="w-6 h-6 text-yellow-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                    <h3 class="font-semibold text-yellow-800">API Key Required</h3>
                    <p class="text-yellow-700 text-sm mt-1">
                        Set the <code class="bg-yellow-100 px-1 rounded">PARASAIL_API_KEY</code> environment variable to enable processing.
                        Get a key from <a href="https://parasail.io" target="_blank" class="underline hover:text-yellow-900">parasail.io</a>
                    </p>
                </div>
            </div>
        </div>

        <!-- Upload Section -->
        <div class="bg-white rounded-2xl shadow-xl p-6 mb-8">
            <!-- Mode Tabs -->
            <div class="flex border-b border-gray-200 mb-6">
                <button onclick="setUploadMode('files')" id="modeFiles"
                    class="px-6 py-3 border-b-2 border-blue-500 text-blue-600 font-medium transition-colors">
                    <span class="flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Upload Files
                    </span>
                </button>
                <button onclick="setUploadMode('folder')" id="modeFolder"
                    class="px-6 py-3 text-gray-500 hover:text-gray-700 font-medium transition-colors">
                    <span class="flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                        </svg>
                        Upload Folder
                    </span>
                </button>
            </div>

            <!-- Options -->
            <div class="grid md:grid-cols-2 gap-4 mb-6">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Batch Name (optional)</label>
                    <input type="text" id="batchName" placeholder="Name for this batch"
                        class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Output Reference (optional)</label>
                    <input type="text" id="outputPath" placeholder="e.g., /documents/output"
                        class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition">
                </div>
            </div>

            <!-- File Upload Area -->
            <div id="fileUploadArea">
                <div id="dropzone" class="dropzone border-2 border-dashed border-gray-300 rounded-xl p-12 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/30 transition-all">
                    <input type="file" id="fileInput" class="hidden" accept=".pdf" multiple>
                    <svg class="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                    </svg>
                    <p class="text-xl text-gray-600 mb-2">Drop PDF files here or click to upload</p>
                    <p class="text-sm text-gray-400">Select multiple PDFs for batch processing</p>
                </div>
            </div>

            <!-- Folder Upload Area -->
            <div id="folderUploadArea" class="hidden">
                <div id="folderDropzone" class="dropzone border-2 border-dashed border-gray-300 rounded-xl p-12 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/30 transition-all">
                    <input type="file" id="folderInput" class="hidden" webkitdirectory directory multiple>
                    <svg class="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                    </svg>
                    <p class="text-xl text-gray-600 mb-2">Click to select a folder</p>
                    <p class="text-sm text-gray-400">All PDFs in the folder and subfolders will be processed</p>
                </div>
            </div>

            <!-- Staged Files -->
            <div id="stagedFiles" class="hidden mt-6 fade-in">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold text-gray-800">
                        Files to Process: <span id="stagedCount" class="text-blue-600">0</span>
                    </h3>
                    <div class="space-x-2">
                        <button onclick="clearStaged()" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition">Clear</button>
                        <button onclick="startProcessing()" id="startBtn" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition shadow-lg shadow-blue-200">
                            Start Processing
                        </button>
                    </div>
                </div>
                <div id="stagedList" class="file-tree bg-gray-50 rounded-lg p-4 max-h-60 overflow-y-auto"></div>
            </div>
        </div>

        <!-- Batches Section -->
        <div id="batchesSection" class="space-y-4 mb-8"></div>

        <!-- Output Section -->
        <div id="outputSection" class="hidden fade-in">
            <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
                <div class="border-b border-gray-200 p-4 flex justify-between items-center bg-gradient-to-r from-blue-50 to-purple-50">
                    <h2 id="outputTitle" class="text-xl font-semibold text-gray-800">Output</h2>
                    <div class="space-x-2">
                        <button onclick="copyOutput()" class="px-4 py-2 bg-white text-gray-700 rounded-lg hover:bg-gray-100 transition border">Copy</button>
                        <button onclick="downloadOutput()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">Download .md</button>
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
        </div> <!-- End mainContent -->
    </div>

    <script>
        let currentOutput = '';
        let currentFilename = '';
        let uploadMode = 'files';
        let stagedFiles = [];
        let activeBatches = {};
        let pollIntervals = {};
        let hasApiKey = true;

        // Check status on load
        async function checkStatus() {
            try {
                const resp = await fetch('/api/status');
                const data = await resp.json();
                hasApiKey = data.has_api_key;

                const badge = document.getElementById('statusBadge');
                const warning = document.getElementById('apiKeyWarning');

                if (!hasApiKey) {
                    warning.classList.remove('hidden');
                    badge.innerHTML = '<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">Setup Required</span>';
                } else {
                    warning.classList.add('hidden');
                    const mode = data.storage_mode === 'cloud' ? 'Cloud' : 'Local';
                    badge.innerHTML = '<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">' + mode + ' Mode Ready</span>';
                }
            } catch (e) {
                console.error('Status check failed:', e);
            }
        }
        checkStatus();

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

            document.getElementById('fileUploadArea').classList.toggle('hidden', mode !== 'files');
            document.getElementById('folderUploadArea').classList.toggle('hidden', mode !== 'folder');
            clearStaged();
        }

        // File upload handlers
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');

        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', async (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            const items = e.dataTransfer.items;
            if (items && items.length > 0) await handleDroppedItems(items);
            else handleFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

        const folderDropzone = document.getElementById('folderDropzone');
        const folderInput = document.getElementById('folderInput');

        folderDropzone.addEventListener('click', () => folderInput.click());
        folderDropzone.addEventListener('dragover', (e) => { e.preventDefault(); folderDropzone.classList.add('dragover'); });
        folderDropzone.addEventListener('dragleave', () => folderDropzone.classList.remove('dragover'));
        folderDropzone.addEventListener('drop', async (e) => {
            e.preventDefault();
            folderDropzone.classList.remove('dragover');
            const items = e.dataTransfer.items;
            if (items && items.length > 0) await handleDroppedItems(items);
        });
        folderInput.addEventListener('change', (e) => handleFolderFiles(e.target.files));

        async function handleDroppedItems(items) {
            const files = [];
            async function traverseEntry(entry, path = '') {
                if (entry.isFile) {
                    return new Promise((resolve) => {
                        entry.file((file) => {
                            if (file.name.toLowerCase().endsWith('.pdf')) {
                                files.push({ file, relativePath: path + file.name, name: file.name });
                            }
                            resolve();
                        });
                    });
                } else if (entry.isDirectory) {
                    const reader = entry.createReader();
                    return new Promise((resolve) => {
                        const readEntries = () => {
                            reader.readEntries(async (entries) => {
                                if (entries.length === 0) resolve();
                                else {
                                    for (const e of entries) await traverseEntry(e, path + entry.name + '/');
                                    readEntries();
                                }
                            });
                        };
                        readEntries();
                    });
                }
            }
            for (const item of items) {
                const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
                if (entry) await traverseEntry(entry);
                else if (item.kind === 'file') {
                    const file = item.getAsFile();
                    if (file && file.name.toLowerCase().endsWith('.pdf')) {
                        files.push({ file, relativePath: null, name: file.name });
                    }
                }
            }
            stagedFiles = stagedFiles.concat(files);
            updateStagedDisplay();
        }

        function handleFiles(files) {
            for (const file of files) {
                if (file.name.toLowerCase().endsWith('.pdf')) {
                    stagedFiles.push({ file, relativePath: null, name: file.name });
                }
            }
            updateStagedDisplay();
        }

        function handleFolderFiles(files) {
            for (const file of files) {
                if (file.name.toLowerCase().endsWith('.pdf')) {
                    const relativePath = file.webkitRelativePath || file.name;
                    stagedFiles.push({ file, relativePath, name: file.name });
                }
            }
            updateStagedDisplay();
        }

        function updateStagedDisplay() {
            const container = document.getElementById('stagedFiles');
            const list = document.getElementById('stagedList');
            const count = document.getElementById('stagedCount');

            if (stagedFiles.length === 0) { container.classList.add('hidden'); return; }

            container.classList.remove('hidden');
            count.textContent = stagedFiles.length;

            const byFolder = {};
            stagedFiles.forEach((item, idx) => {
                const path = item.relativePath || '';
                const parts = path.split('/');
                const folder = parts.length > 1 ? parts.slice(0, -1).join('/') : '(root)';
                if (!byFolder[folder]) byFolder[folder] = [];
                byFolder[folder].push({ ...item, idx });
            });

            const sortedFolders = Object.keys(byFolder).sort((a, b) => {
                if (a === '(root)') return -1;
                if (b === '(root)') return 1;
                return a.localeCompare(b);
            });

            let html = '';
            for (const folder of sortedFolders) {
                const files = byFolder[folder];
                if (folder !== '(root)') html += '<div class="font-bold text-gray-700 mt-2">📁 ' + folder + '/</div>';
                for (const f of files) {
                    html += '<div class="flex justify-between items-center pl-4 py-1 hover:bg-gray-100 rounded"><span>📄 ' + f.name + '</span><button onclick="removeStaged(' + f.idx + ')" class="text-red-500 hover:text-red-700 px-2">×</button></div>';
                }
            }
            list.innerHTML = html;
        }

        function removeStaged(idx) { stagedFiles.splice(idx, 1); updateStagedDisplay(); }
        function clearStaged() { stagedFiles = []; updateStagedDisplay(); fileInput.value = ''; folderInput.value = ''; }

        async function startProcessing() {
            if (stagedFiles.length === 0) return;
            if (!hasApiKey) { alert('Please set PARASAIL_API_KEY environment variable first.'); return; }

            const startBtn = document.getElementById('startBtn');
            startBtn.disabled = true;
            startBtn.textContent = 'Uploading...';

            const outputPath = document.getElementById('outputPath').value.trim();
            const batchNameInput = document.getElementById('batchName').value.trim();

            const formData = new FormData();
            const relativePaths = [];

            for (const item of stagedFiles) {
                formData.append('files', item.file);
                relativePaths.push(item.relativePath || null);
            }

            formData.append('relative_paths', JSON.stringify(relativePaths));
            if (outputPath) formData.append('output_path', outputPath);

            let batchName = batchNameInput || (uploadMode === 'folder'
                ? 'Folder: ' + (stagedFiles[0]?.relativePath?.split('/')[0] || 'Upload')
                : stagedFiles.length + ' file' + (stagedFiles.length > 1 ? 's' : ''));
            formData.append('batch_name', batchName);

            try {
                const response = await fetch('/api/upload-multiple', { method: 'POST', body: formData });
                const data = await response.json();

                if (response.ok) {
                    if (data.errors?.length) alert('Some files had issues:\\n' + data.errors.join('\\n'));
                    pollBatch(data.batch_id);
                    clearStaged();
                    document.getElementById('batchName').value = '';
                } else {
                    alert('Upload failed: ' + (data.detail || 'Unknown error'));
                }
            } catch (error) {
                alert('Upload failed: ' + error.message);
            } finally {
                startBtn.disabled = false;
                startBtn.textContent = 'Start Processing';
            }
        }

        async function pollBatch(batchId) {
            const poll = async () => {
                try {
                    const response = await fetch('/api/batch/' + batchId);
                    if (!response.ok) return;
                    const batch = await response.json();
                    activeBatches[batchId] = batch;
                    renderBatches();
                    if (batch.status === 'processing' || batch.status === 'pending') {
                        pollIntervals[batchId] = setTimeout(poll, 1500);
                    }
                } catch (error) {
                    pollIntervals[batchId] = setTimeout(poll, 3000);
                }
            };
            poll();
        }

        function renderBatches() {
            const container = document.getElementById('batchesSection');
            const batchList = Object.values(activeBatches).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            if (batchList.length === 0) {
                container.innerHTML = '<div class="text-center text-gray-500 py-8 bg-white rounded-xl shadow">No batches yet. Upload some PDFs to get started!</div>';
                return;
            }

            container.innerHTML = batchList.map(batch => {
                const jobs = batch.jobs || [];
                const completedJobs = jobs.filter(j => j.status === 'completed').length;
                const failedJobs = jobs.filter(j => j.status === 'failed').length;
                const processingJobs = jobs.filter(j => j.status === 'processing').length;
                const queuedJobs = jobs.filter(j => j.status === 'queued' || j.status === 'pending').length;
                const overallProgress = batch.total_files > 0 ? Math.round((batch.completed_files / batch.total_files) * 100) : 0;
                const canDownloadAll = completedJobs > 0;

                return '<div class="bg-white rounded-xl shadow-lg p-6 fade-in"><div class="flex justify-between items-start mb-4"><div class="flex-1"><h3 class="text-lg font-semibold text-gray-800">' + (batch.name || 'Batch') + '</h3><div class="flex flex-wrap gap-2 mt-1 text-sm">' +
                    (completedJobs > 0 ? '<span class="text-green-600">' + completedJobs + ' completed</span>' : '') +
                    (processingJobs > 0 ? '<span class="text-blue-600">' + processingJobs + ' processing</span>' : '') +
                    (queuedJobs > 0 ? '<span class="text-gray-500">' + queuedJobs + ' queued</span>' : '') +
                    (failedJobs > 0 ? '<span class="text-red-500">' + failedJobs + ' failed</span>' : '') +
                    '</div></div><div class="flex items-center gap-2"><span class="px-3 py-1 rounded-full text-sm font-medium status-' + batch.status + '">' + batch.status + '</span>' +
                    (canDownloadAll ? '<button onclick="downloadAllOutputs(\'' + batch.id + '\')" class="px-3 py-1 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm font-medium">Download All</button>' : '') +
                    '<button onclick="deleteBatch(\'' + batch.id + '\')" class="text-red-500 hover:text-red-700 text-xl px-2">×</button></div></div>' +
                    '<div class="mb-4"><div class="flex justify-between text-xs text-gray-500 mb-1"><span>Progress: ' + batch.completed_files + '/' + batch.total_files + '</span><span>' + overallProgress + '%</span></div><div class="bg-gray-200 rounded-full h-2"><div class="bg-gradient-to-r from-blue-500 to-purple-500 rounded-full h-2 transition-all duration-300" style="width: ' + overallProgress + '%"></div></div></div>' +
                    '<div class="space-y-2 max-h-80 overflow-y-auto">' + (jobs.length === 0 ? '<div class="text-center text-gray-400 py-4">Loading jobs...</div>' : jobs.map(job => {
                        return '<div class="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"><div class="flex-1 min-w-0"><div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full dot-' + job.status + '"></span><p class="text-sm font-medium text-gray-800 truncate">' + job.filename + '</p></div>' +
                            (job.relative_path ? '<p class="text-xs text-gray-400 truncate ml-4">' + job.relative_path + '</p>' : '') +
                            (job.status === 'processing' ? '<div class="mt-1 ml-4 flex items-center gap-2"><div class="flex-1 bg-gray-200 rounded-full h-1.5"><div class="bg-blue-500 rounded-full h-1.5 transition-all" style="width: ' + (job.progress || 0) + '%"></div></div><span class="text-xs text-gray-500 whitespace-nowrap">' + (job.current_page || 0) + '/' + (job.total_pages || '?') + ' pages</span></div>' : '') +
                            (job.status === 'failed' && job.error ? '<p class="text-xs text-red-500 ml-4 mt-1">Error: ' + job.error + '</p>' : '') +
                            '</div><div class="flex items-center gap-2 ml-4">' +
                            (job.status === 'completed' ? '<button onclick="viewOutput(\'' + job.id + '\')" class="px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm">View</button><button onclick="downloadJobOutput(\'' + job.id + '\', \'' + job.filename.replace(/'/g, "\\'") + '\')" class="px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm">.md</button>' : '') +
                            '<span class="text-xs text-gray-400 capitalize">' + job.status + '</span></div></div>';
                    }).join('')) + '</div></div>';
            }).join('');
        }

        async function viewOutput(jobId) {
            try {
                const response = await fetch('/api/jobs/' + jobId + '/output');
                if (!response.ok) { alert('Failed to load output'); return; }
                const data = await response.json();
                currentOutput = data.text;
                currentFilename = data.filename.replace(/\\.pdf$/i, '.md');
                document.getElementById('outputSection').classList.remove('hidden');
                document.getElementById('outputTitle').textContent = data.filename;
                document.getElementById('renderedOutput').innerHTML = marked.parse(data.text);
                document.getElementById('rawOutput').querySelector('pre').textContent = data.text;
                document.getElementById('outputSection').scrollIntoView({ behavior: 'smooth' });
            } catch (error) {
                alert('Failed to load output: ' + error.message);
            }
        }

        async function downloadJobOutput(jobId, filename) {
            try {
                const response = await fetch('/api/jobs/' + jobId + '/output');
                if (!response.ok) { alert('Failed to download'); return; }
                const data = await response.json();
                const blob = new Blob([data.text], { type: 'text/markdown' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename.replace(/\\.pdf$/i, '.md');
                a.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                alert('Download failed');
            }
        }

        async function downloadAllOutputs(batchId) {
            const batch = activeBatches[batchId];
            if (!batch || !batch.jobs) return;
            const completedJobs = batch.jobs.filter(j => j.status === 'completed');
            if (completedJobs.length === 0) { alert('No completed jobs to download'); return; }
            if (completedJobs.length === 1) { await downloadJobOutput(completedJobs[0].id, completedJobs[0].filename); return; }

            try {
                const zip = new JSZip();
                for (const job of completedJobs) {
                    const response = await fetch('/api/jobs/' + job.id + '/output');
                    if (!response.ok) continue;
                    const data = await response.json();
                    let filepath = job.filename.replace(/\\.pdf$/i, '.md');
                    if (job.relative_path) filepath = job.relative_path.replace(/\\.pdf$/i, '.md');
                    zip.file(filepath, data.text);
                }
                const content = await zip.generateAsync({ type: 'blob' });
                const url = URL.createObjectURL(content);
                const a = document.createElement('a');
                a.href = url;
                a.download = (batch.name || 'batch') + '.zip';
                a.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                alert('Failed to create zip file');
            }
        }

        async function deleteBatch(batchId) {
            if (!confirm('Delete this batch and all its jobs?')) return;
            if (pollIntervals[batchId]) { clearTimeout(pollIntervals[batchId]); delete pollIntervals[batchId]; }
            try {
                await fetch('/api/batch/' + batchId, { method: 'DELETE' });
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
                rendered.classList.remove('hidden'); raw.classList.add('hidden');
                tabRendered.classList.add('border-b-2', 'border-blue-500', 'text-blue-600');
                tabRaw.classList.remove('border-b-2', 'border-blue-500', 'text-blue-600');
            } else {
                rendered.classList.add('hidden'); raw.classList.remove('hidden');
                tabRaw.classList.add('border-b-2', 'border-blue-500', 'text-blue-600');
                tabRendered.classList.remove('border-b-2', 'border-blue-500', 'text-blue-600');
            }
        }

        function copyOutput() { navigator.clipboard.writeText(currentOutput); alert('Copied to clipboard!'); }
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
                if (!response.ok) return;
                const batches = await response.json();
                for (const batch of batches) {
                    if (batch.status === 'processing' || batch.status === 'pending') {
                        pollBatch(batch.id);
                    } else {
                        const fullResponse = await fetch('/api/batch/' + batch.id);
                        if (fullResponse.ok) activeBatches[batch.id] = await fullResponse.json();
                    }
                }
                renderBatches();
            } catch (error) {
                console.error('Failed to load batches:', error);
            }
        }

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

    print("\n" + "=" * 60)
    print("  olmOCR Batch Processor v3.0")
    print("=" * 60)
    print("\n  FEATURES:")
    print(f"    - Parallel processing ({MAX_CONCURRENT_PAGES} pages concurrent)")
    print("    - Persistent jobs (survive browser close)")
    print("    - Folder uploads with structure preservation")
    print("    - Beautiful web interface")

    print("\n  STORAGE MODE:", end=" ")
    if STORAGE_MODE == "cloud" or GCP_PROJECT_ID:
        print("Cloud (Firestore + GCS)")
    else:
        print(f"Local (SQLite + filesystem)")
        print(f"    - Database: {DB_PATH}")
        print(f"    - PDFs: {PDF_DIR}")
        print(f"    - Outputs: {OUTPUT_DIR}")

    print("\n  API KEY:", "Configured" if PARASAIL_API_KEY else "NOT SET")

    if not PARASAIL_API_KEY:
        print("\n  ⚠️  WARNING: PARASAIL_API_KEY not set!")
        print("     Get a key from https://parasail.io")
        print("     Then run: export PARASAIL_API_KEY='your-key'")

    print(f"\n  Open http://localhost:{port} in your browser")
    print("\n  Press Ctrl+C to stop\n")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=port)
