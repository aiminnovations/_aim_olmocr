"""
File browser router.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.middleware.auth import get_current_user
from app.models.file import (
    FolderContents,
    CreateFolderRequest,
    DeleteFilesRequest,
    MoveFilesRequest,
    CopyFilesRequest,
    RenameFileRequest,
)
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/browse/{path:path}", response_model=FolderContents)
async def browse_folder(
    path: str = "",
    current_user: dict = Depends(get_current_user),
):
    """List contents of a folder."""
    user_id = current_user["uid"]

    try:
        contents = await storage_service.list_contents(user_id, path)
        return contents
    except Exception as e:
        logger.error(f"Error browsing folder {path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list folder contents")


@router.post("/folders", status_code=201)
async def create_folder(
    request: CreateFolderRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new folder."""
    user_id = current_user["uid"]

    try:
        await storage_service.create_folder(user_id, request.path)
        return {"message": "Folder created successfully", "path": request.path}
    except Exception as e:
        logger.error(f"Error creating folder {request.path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create folder")


@router.post("/files/delete")
async def delete_files(
    request: DeleteFilesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Delete files or folders."""
    user_id = current_user["uid"]

    try:
        deleted_count = await storage_service.delete_items(user_id, request.paths)
        return {"message": f"Deleted {deleted_count} items", "count": deleted_count}
    except Exception as e:
        logger.error(f"Error deleting files: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete files")


@router.post("/files/move")
async def move_files(
    request: MoveFilesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Move files or folders."""
    user_id = current_user["uid"]

    try:
        moved_count = await storage_service.move_items(
            user_id,
            request.source_paths,
            request.destination,
        )
        return {"message": f"Moved {moved_count} items", "count": moved_count}
    except Exception as e:
        logger.error(f"Error moving files: {e}")
        raise HTTPException(status_code=500, detail="Failed to move files")


@router.post("/files/copy")
async def copy_files(
    request: CopyFilesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Copy files or folders."""
    user_id = current_user["uid"]

    try:
        copied_count = await storage_service.copy_items(
            user_id,
            request.source_paths,
            request.destination,
        )
        return {"message": f"Copied {copied_count} items", "count": copied_count}
    except Exception as e:
        logger.error(f"Error copying files: {e}")
        raise HTTPException(status_code=500, detail="Failed to copy files")


@router.post("/files/rename")
async def rename_file(
    request: RenameFileRequest,
    current_user: dict = Depends(get_current_user),
):
    """Rename a file or folder."""
    user_id = current_user["uid"]

    try:
        await storage_service.rename_item(
            user_id,
            request.old_path,
            request.new_name,
        )
        return {"message": "Item renamed successfully"}
    except Exception as e:
        logger.error(f"Error renaming file: {e}")
        raise HTTPException(status_code=500, detail="Failed to rename file")
