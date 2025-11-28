"""
Processing job router.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import pubsub_v1

from app.config import settings
from app.middleware.auth import get_current_user
from app.models.job import (
    Job,
    JobListResponse,
    CreateJobRequest,
    JobStatus,
)
from app.services.firestore import firestore_service
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Pub/Sub publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(settings.gcp_project_id, settings.pubsub_topic)


@router.post("/process", response_model=Job, status_code=201)
async def create_job(
    request: CreateJobRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new processing job."""
    user_id = current_user["uid"]

    try:
        # Verify input file exists
        exists = await storage_service.file_exists(user_id, request.input_path)
        if not exists:
            raise HTTPException(
                status_code=404,
                detail=f"Input file not found: {request.input_path}",
            )

        # Create job in Firestore
        job = await firestore_service.create_job(
            user_id=user_id,
            input_path=request.input_path,
            output_path=request.output_path,
            output_format=request.output_format,
            options=request.options.model_dump() if request.options else None,
        )

        # Publish job to Pub/Sub
        message_data = {
            "job_id": job.id,
            "user_id": user_id,
            "input_path": request.input_path,
            "output_path": request.output_path,
            "output_format": request.output_format,
            "options": request.options.model_dump() if request.options else {},
        }

        future = publisher.publish(
            topic_path,
            json.dumps(message_data).encode("utf-8"),
        )
        message_id = future.result()

        logger.info(f"Published job {job.id} to Pub/Sub, message ID: {message_id}")

        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create processing job")


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = None,
    current_user: dict = Depends(get_current_user),
):
    """List processing jobs for the current user."""
    user_id = current_user["uid"]

    try:
        jobs, total = await firestore_service.list_jobs(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
        )

        total_pages = (total + page_size - 1) // page_size

        return JobListResponse(
            jobs=jobs,
            total=total,
            page=page,
            pageSize=page_size,
            totalPages=total_pages,
        )
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific job by ID."""
    user_id = current_user["uid"]

    try:
        job = await firestore_service.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Verify ownership
        if job.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job")


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Cancel a pending or processing job."""
    user_id = current_user["uid"]

    try:
        success = await firestore_service.cancel_job(job_id, user_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Job not found or cannot be cancelled",
            )

        return {"message": "Job cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/jobs/{job_id}/output")
async def get_job_output(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get output files for a completed job."""
    user_id = current_user["uid"]

    try:
        job = await firestore_service.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Verify ownership
        if job.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if job is completed
        if job.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed (status: {job.status})",
            )

        # Generate signed URLs for output files
        output_files = []
        for file_info in job.output.files:
            url, expires_at = await storage_service.generate_signed_download_url(
                user_id,
                file_info.path,
            )
            output_files.append({
                "name": file_info.name,
                "path": file_info.path,
                "size": file_info.size,
                "download_url": url,
                "expires_at": expires_at.isoformat(),
            })

        return {
            "job_id": job_id,
            "output_path": job.output.path,
            "format": job.output.format,
            "files": output_files,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job output {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job output")
