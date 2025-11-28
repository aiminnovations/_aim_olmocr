"""
Download router.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


class BatchDownloadRequest(BaseModel):
    """Request for batch download."""
    file_ids: List[str] = Field(..., alias="fileIds", min_items=1, max_items=50)


@router.get("/download/{file_path:path}")
async def get_download_url(
    file_path: str,
    current_user: dict = Depends(get_current_user),
):
    """Generate a signed download URL for a file."""
    user_id = current_user["uid"]

    try:
        # Verify file exists
        exists = await storage_service.file_exists(user_id, file_path)
        if not exists:
            raise HTTPException(status_code=404, detail="File not found")

        # Generate signed URL
        url, expires_at = await storage_service.generate_signed_download_url(
            user_id,
            file_path,
        )

        return {
            "url": url,
            "expires_at": expires_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate download URL")


@router.post("/download/batch")
async def batch_download(
    request: BatchDownloadRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate signed download URLs for multiple files.

    Note: For a true batch download (ZIP), you would need a Cloud Function
    or additional service to create the archive. This endpoint returns
    individual URLs for each file.
    """
    user_id = current_user["uid"]

    try:
        downloads = []

        for file_path in request.file_ids:
            # Verify file exists
            exists = await storage_service.file_exists(user_id, file_path)
            if not exists:
                downloads.append({
                    "path": file_path,
                    "error": "File not found",
                })
                continue

            # Generate signed URL
            url, expires_at = await storage_service.generate_signed_download_url(
                user_id,
                file_path,
            )

            downloads.append({
                "path": file_path,
                "url": url,
                "expires_at": expires_at.isoformat(),
            })

        return {"downloads": downloads}
    except Exception as e:
        logger.error(f"Error generating batch download URLs: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate download URLs")
