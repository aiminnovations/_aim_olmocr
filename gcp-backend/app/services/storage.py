"""
Google Cloud Storage service.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from google.cloud import storage
from google.cloud.storage import Blob

from app.config import settings
from app.models.file import FileItem, FolderItem, FolderContents

logger = logging.getLogger(__name__)


class StorageService:
    """Service for Google Cloud Storage operations."""

    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(settings.gcs_bucket)

    def _get_user_prefix(self, user_id: str) -> str:
        """Get the storage prefix for a user."""
        return f"users/{user_id}/"

    def _blob_to_file_item(self, blob: Blob) -> FileItem:
        """Convert a GCS blob to a FileItem."""
        name = blob.name.split("/")[-1]
        extension = name.split(".")[-1] if "." in name else None

        return FileItem(
            id=hashlib.md5(blob.name.encode()).hexdigest(),
            name=name,
            path=blob.name,
            size=blob.size or 0,
            modified=blob.updated or datetime.utcnow(),
            content_type=blob.content_type or "application/octet-stream",
            extension=extension,
        )

    def _prefix_to_folder_item(self, prefix: str, base_prefix: str) -> FolderItem:
        """Convert a GCS prefix to a FolderItem."""
        # Remove trailing slash and get name
        clean_prefix = prefix.rstrip("/")
        name = clean_prefix.split("/")[-1]

        return FolderItem(
            id=hashlib.md5(prefix.encode()).hexdigest(),
            name=name,
            path=clean_prefix,
        )

    async def list_contents(
        self,
        user_id: str,
        path: str = ""
    ) -> FolderContents:
        """List contents of a folder."""
        user_prefix = self._get_user_prefix(user_id)

        # Build the full prefix
        if path:
            full_prefix = f"{user_prefix}{path}/"
        else:
            full_prefix = user_prefix

        # Ensure prefix doesn't have double slashes
        full_prefix = "/".join(filter(None, full_prefix.split("/"))) + "/"

        logger.info(f"Listing contents at prefix: {full_prefix}")

        # List blobs with delimiter to get folders
        blobs = self.client.list_blobs(
            self.bucket.name,
            prefix=full_prefix,
            delimiter="/",
        )

        files: List[FileItem] = []
        folders: List[FolderItem] = []

        # Process files
        for blob in blobs:
            # Skip folder markers
            if blob.name.endswith("/"):
                continue
            # Skip the prefix itself
            if blob.name == full_prefix:
                continue
            files.append(self._blob_to_file_item(blob))

        # Process folders (prefixes)
        for prefix in blobs.prefixes:
            folders.append(self._prefix_to_folder_item(prefix, full_prefix))

        # Calculate parent path
        parent = None
        if path:
            parent_parts = path.rstrip("/").split("/")[:-1]
            parent = "/".join(parent_parts) if parent_parts else ""

        return FolderContents(
            path=path,
            files=files,
            folders=folders,
            parent=parent,
        )

    async def create_folder(self, user_id: str, path: str) -> bool:
        """Create a folder (empty object with trailing slash)."""
        user_prefix = self._get_user_prefix(user_id)
        full_path = f"{user_prefix}{path}/"

        # Ensure path doesn't have double slashes
        full_path = "/".join(filter(None, full_path.split("/"))) + "/"

        blob = self.bucket.blob(full_path)
        blob.upload_from_string("")

        logger.info(f"Created folder: {full_path}")
        return True

    async def delete_items(self, user_id: str, paths: List[str]) -> int:
        """Delete files or folders."""
        user_prefix = self._get_user_prefix(user_id)
        deleted_count = 0

        for path in paths:
            full_path = f"{user_prefix}{path}"

            # Check if it's a folder (prefix)
            blobs = list(self.client.list_blobs(
                self.bucket.name,
                prefix=full_path,
                max_results=1000,
            ))

            if blobs:
                # Delete all blobs under this prefix
                for blob in blobs:
                    blob.delete()
                    deleted_count += 1
            else:
                # Try to delete as a single file
                blob = self.bucket.blob(full_path)
                if blob.exists():
                    blob.delete()
                    deleted_count += 1

        logger.info(f"Deleted {deleted_count} items")
        return deleted_count

    async def move_items(
        self,
        user_id: str,
        source_paths: List[str],
        destination: str
    ) -> int:
        """Move files or folders."""
        user_prefix = self._get_user_prefix(user_id)
        moved_count = 0

        for source_path in source_paths:
            source_full = f"{user_prefix}{source_path}"
            source_name = source_path.split("/")[-1]
            dest_full = f"{user_prefix}{destination}/{source_name}"

            # List all blobs under source
            blobs = list(self.client.list_blobs(
                self.bucket.name,
                prefix=source_full,
            ))

            for blob in blobs:
                # Calculate new path
                relative_path = blob.name[len(source_full):]
                new_path = f"{dest_full}{relative_path}"

                # Copy to new location
                self.bucket.copy_blob(blob, self.bucket, new_path)

                # Delete original
                blob.delete()
                moved_count += 1

        logger.info(f"Moved {moved_count} items")
        return moved_count

    async def copy_items(
        self,
        user_id: str,
        source_paths: List[str],
        destination: str
    ) -> int:
        """Copy files or folders."""
        user_prefix = self._get_user_prefix(user_id)
        copied_count = 0

        for source_path in source_paths:
            source_full = f"{user_prefix}{source_path}"
            source_name = source_path.split("/")[-1]
            dest_full = f"{user_prefix}{destination}/{source_name}"

            # List all blobs under source
            blobs = list(self.client.list_blobs(
                self.bucket.name,
                prefix=source_full,
            ))

            for blob in blobs:
                # Calculate new path
                relative_path = blob.name[len(source_full):]
                new_path = f"{dest_full}{relative_path}"

                # Copy to new location
                self.bucket.copy_blob(blob, self.bucket, new_path)
                copied_count += 1

        logger.info(f"Copied {copied_count} items")
        return copied_count

    async def rename_item(
        self,
        user_id: str,
        old_path: str,
        new_name: str
    ) -> bool:
        """Rename a file or folder."""
        user_prefix = self._get_user_prefix(user_id)
        old_full = f"{user_prefix}{old_path}"

        # Calculate new path
        path_parts = old_path.split("/")
        path_parts[-1] = new_name
        new_path = "/".join(path_parts)
        new_full = f"{user_prefix}{new_path}"

        # List all blobs under old path
        blobs = list(self.client.list_blobs(
            self.bucket.name,
            prefix=old_full,
        ))

        for blob in blobs:
            # Calculate new path
            relative_path = blob.name[len(old_full):]
            target_path = f"{new_full}{relative_path}"

            # Copy to new location
            self.bucket.copy_blob(blob, self.bucket, target_path)

            # Delete original
            blob.delete()

        logger.info(f"Renamed {old_path} to {new_path}")
        return True

    async def generate_signed_upload_url(
        self,
        user_id: str,
        path: str,
        content_type: str,
        expiration: int = 3600,
    ) -> Tuple[str, str, datetime]:
        """Generate a signed URL for uploading."""
        user_prefix = self._get_user_prefix(user_id)
        full_path = f"{user_prefix}{path}"

        blob = self.bucket.blob(full_path)
        expires_at = datetime.utcnow() + timedelta(seconds=expiration)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration),
            method="PUT",
            content_type=content_type,
        )

        return url, full_path, expires_at

    async def generate_signed_download_url(
        self,
        user_id: str,
        path: str,
        expiration: int = 3600,
    ) -> Tuple[str, datetime]:
        """Generate a signed URL for downloading."""
        user_prefix = self._get_user_prefix(user_id)
        full_path = f"{user_prefix}{path}"

        blob = self.bucket.blob(full_path)
        expires_at = datetime.utcnow() + timedelta(seconds=expiration)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration),
            method="GET",
        )

        return url, expires_at

    async def file_exists(self, user_id: str, path: str) -> bool:
        """Check if a file exists."""
        user_prefix = self._get_user_prefix(user_id)
        full_path = f"{user_prefix}{path}"

        blob = self.bucket.blob(full_path)
        return blob.exists()


# Singleton instance
storage_service = StorageService()
