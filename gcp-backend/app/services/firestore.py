"""
Firestore service for user data and job management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

from google.cloud import firestore
from google.cloud.firestore_v1 import AsyncClient

from app.config import settings
from app.models.job import Job, JobStatus, JobProgress, JobInput, JobOutput, JobMetrics

logger = logging.getLogger(__name__)


class FirestoreService:
    """Service for Firestore operations."""

    def __init__(self):
        self.db = firestore.AsyncClient(project=settings.gcp_project_id)

    # User Settings
    async def get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user settings."""
        doc_ref = self.db.collection("users").document(user_id)
        doc = await doc_ref.get()

        if doc.exists:
            return doc.to_dict().get("settings", {})
        return None

    async def update_user_settings(
        self,
        user_id: str,
        settings_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user settings."""
        doc_ref = self.db.collection("users").document(user_id)

        await doc_ref.set(
            {
                "settings": settings_data,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

        return settings_data

    async def ensure_user_exists(self, user_id: str, email: str) -> None:
        """Ensure user document exists with default settings."""
        doc_ref = self.db.collection("users").document(user_id)
        doc = await doc_ref.get()

        if not doc.exists:
            await doc_ref.set({
                "email": email,
                "created_at": firestore.SERVER_TIMESTAMP,
                "last_active": firestore.SERVER_TIMESTAMP,
                "settings": {
                    "default_input_path": "input",
                    "default_output_path": "output",
                    "default_output_format": "markdown",
                    "email_notifications": True,
                    "theme": "system",
                },
                "quotas": {
                    "storage_used": 0,
                    "storage_limit": 10 * 1024 * 1024 * 1024,  # 10GB
                    "pages_processed": 0,
                    "monthly_limit": 10000,
                },
            })

    # Job Management
    async def create_job(
        self,
        user_id: str,
        input_path: str,
        output_path: str,
        output_format: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """Create a new processing job."""
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()

        job_data = {
            "id": job_id,
            "user_id": user_id,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
            "input": {
                "path": input_path,
                "file_name": input_path.split("/")[-1],
                "file_size": 0,  # Will be updated
                "page_count": 0,  # Will be updated
            },
            "output": {
                "path": output_path,
                "format": output_format,
                "files": [],
            },
            "progress": {
                "current": 0,
                "total": 0,
                "percentage": 0,
            },
            "metrics": None,
            "error": None,
            "options": options or {},
        }

        doc_ref = self.db.collection("jobs").document(job_id)
        await doc_ref.set(job_data)

        logger.info(f"Created job {job_id} for user {user_id}")

        return Job(
            id=job_id,
            userId=user_id,
            status="pending",
            createdAt=now,
            updatedAt=now,
            input=JobInput(
                path=input_path,
                fileName=input_path.split("/")[-1],
                fileSize=0,
                pageCount=0,
            ),
            output=JobOutput(
                path=output_path,
                format=output_format,
                files=[],
            ),
            progress=JobProgress(),
        )

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        doc_ref = self.db.collection("jobs").document(job_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        return self._dict_to_job(data)

    async def list_jobs(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[JobStatus] = None,
    ) -> tuple[List[Job], int]:
        """List jobs for a user with pagination."""
        query = (
            self.db.collection("jobs")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
        )

        if status:
            query = query.where("status", "==", status)

        # Get total count
        count_query = query.count()
        count_result = await count_query.get()
        total = count_result[0][0].value

        # Get paginated results
        offset = (page - 1) * page_size
        docs = await query.offset(offset).limit(page_size).get()

        jobs = [self._dict_to_job(doc.to_dict()) for doc in docs]

        return jobs, total

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update job status."""
        doc_ref = self.db.collection("jobs").document(job_id)

        update_data: Dict[str, Any] = {
            "status": status,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        if status == "processing":
            update_data["started_at"] = firestore.SERVER_TIMESTAMP
        elif status in ("completed", "failed", "cancelled"):
            update_data["completed_at"] = firestore.SERVER_TIMESTAMP

        if error:
            update_data["error"] = error

        if metrics:
            update_data["metrics"] = metrics

        await doc_ref.update(update_data)
        logger.info(f"Updated job {job_id} status to {status}")

    async def update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int,
    ) -> None:
        """Update job progress."""
        percentage = int((current / total) * 100) if total > 0 else 0

        doc_ref = self.db.collection("jobs").document(job_id)
        await doc_ref.update({
            "progress": {
                "current": current,
                "total": total,
                "percentage": percentage,
            },
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    async def add_job_output_file(
        self,
        job_id: str,
        file_name: str,
        file_path: str,
        file_size: int,
    ) -> None:
        """Add an output file to a job."""
        doc_ref = self.db.collection("jobs").document(job_id)
        await doc_ref.update({
            "output.files": firestore.ArrayUnion([{
                "name": file_name,
                "path": file_path,
                "size": file_size,
            }]),
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel a job if it belongs to the user and is cancellable."""
        doc_ref = self.db.collection("jobs").document(job_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return False

        data = doc.to_dict()
        if data["user_id"] != user_id:
            return False

        if data["status"] not in ("pending", "processing"):
            return False

        await doc_ref.update({
            "status": "cancelled",
            "updated_at": firestore.SERVER_TIMESTAMP,
            "completed_at": firestore.SERVER_TIMESTAMP,
        })

        logger.info(f"Cancelled job {job_id}")
        return True

    def _dict_to_job(self, data: Dict[str, Any]) -> Job:
        """Convert a Firestore document dict to a Job model."""
        input_data = data.get("input", {})
        output_data = data.get("output", {})
        progress_data = data.get("progress", {})
        metrics_data = data.get("metrics")

        return Job(
            id=data["id"],
            userId=data["user_id"],
            status=data["status"],
            createdAt=data["created_at"],
            updatedAt=data["updated_at"],
            startedAt=data.get("started_at"),
            completedAt=data.get("completed_at"),
            input=JobInput(
                path=input_data.get("path", ""),
                fileName=input_data.get("file_name", ""),
                fileSize=input_data.get("file_size", 0),
                pageCount=input_data.get("page_count", 0),
            ),
            output=JobOutput(
                path=output_data.get("path", ""),
                format=output_data.get("format", "markdown"),
                files=output_data.get("files", []),
            ),
            progress=JobProgress(
                current=progress_data.get("current", 0),
                total=progress_data.get("total", 0),
                percentage=progress_data.get("percentage", 0),
            ),
            metrics=JobMetrics(
                inputTokens=metrics_data.get("input_tokens", 0),
                outputTokens=metrics_data.get("output_tokens", 0),
                processingTimeMs=metrics_data.get("processing_time_ms", 0),
            ) if metrics_data else None,
            error=data.get("error"),
        )


# Singleton instance
firestore_service = FirestoreService()
