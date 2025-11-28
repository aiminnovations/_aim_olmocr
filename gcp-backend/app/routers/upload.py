"""
File upload router.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth import get_current_user
from app.models.file import InitUploadRequest, InitUploadResponse, CompleteUploadRequest
from app.services.storage import storage_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed content types for upload
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
}


@router.post("/upload/init", response_model=InitUploadResponse)
async def init_upload(
    request: InitUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    """Initialize a file upload and get a signed URL."""
    user_id = current_user["uid"]

    # Validate content type
    if request.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Content type '{request.content_type}' is not allowed. "
                   f"Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # Validate file size
    if request.file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of "
                   f"{settings.max_upload_size / (1024*1024):.0f}MB",
        )

    try:
        # Build the full path
        if request.destination_path:
            full_path = f"{request.destination_path}/{request.file_name}"
        else:
            full_path = f"input/{request.file_name}"

        # Generate signed URL
        signed_url, path, expires_at = await storage_service.generate_signed_upload_url(
            user_id,
            full_path,
            request.content_type,
            expiration=settings.signed_url_expiration,
        )

        logger.info(f"Generated upload URL for user {user_id}: {path}")

        return InitUploadResponse(
            signedUrl=signed_url,
            path=full_path,
            expiresAt=expires_at,
        )
    except Exception as e:
        logger.error(f"Error initializing upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize upload")


@router.post("/upload/complete")
async def complete_upload(
    request: CompleteUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    """Mark an upload as complete."""
    user_id = current_user["uid"]

    try:
        # Verify the file exists
        exists = await storage_service.file_exists(user_id, request.path)

        if not exists:
            raise HTTPException(
                status_code=404,
                detail="Uploaded file not found. Upload may have failed.",
            )

        logger.info(f"Upload completed for user {user_id}: {request.path}")

        return {"message": "Upload completed successfully", "path": request.path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete upload")
