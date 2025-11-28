"""
File and folder models.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class FileItem(BaseModel):
    """Represents a file in storage."""
    id: str
    name: str
    path: str
    type: Literal["file"] = "file"
    size: int
    modified: datetime
    content_type: str
    extension: Optional[str] = None


class FolderItem(BaseModel):
    """Represents a folder in storage."""
    id: str
    name: str
    path: str
    type: Literal["folder"] = "folder"


class FolderContents(BaseModel):
    """Contents of a folder."""
    path: str
    files: List[FileItem]
    folders: List[FolderItem]
    parent: Optional[str] = None


class CreateFolderRequest(BaseModel):
    """Request to create a folder."""
    path: str = Field(..., min_length=1, max_length=500)


class DeleteFilesRequest(BaseModel):
    """Request to delete files."""
    paths: List[str] = Field(..., min_items=1, max_items=100)


class MoveFilesRequest(BaseModel):
    """Request to move files."""
    source_paths: List[str] = Field(..., alias="sourcePaths", min_items=1, max_items=100)
    destination: str = Field(..., min_length=1, max_length=500)


class CopyFilesRequest(BaseModel):
    """Request to copy files."""
    source_paths: List[str] = Field(..., alias="sourcePaths", min_items=1, max_items=100)
    destination: str = Field(..., min_length=1, max_length=500)


class RenameFileRequest(BaseModel):
    """Request to rename a file."""
    old_path: str = Field(..., alias="oldPath", min_length=1, max_length=500)
    new_name: str = Field(..., alias="newName", min_length=1, max_length=255)


class InitUploadRequest(BaseModel):
    """Request to initialize a file upload."""
    file_name: str = Field(..., alias="fileName", min_length=1, max_length=255)
    content_type: str = Field(..., alias="contentType")
    destination_path: str = Field(..., alias="destinationPath", min_length=0, max_length=500)
    file_size: int = Field(..., alias="fileSize", gt=0)


class InitUploadResponse(BaseModel):
    """Response for upload initialization."""
    signed_url: str = Field(..., alias="signedUrl")
    path: str
    expires_at: datetime = Field(..., alias="expiresAt")


class CompleteUploadRequest(BaseModel):
    """Request to complete a file upload."""
    path: str = Field(..., min_length=1, max_length=500)
