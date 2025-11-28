"""
User settings router.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user
from app.services.firestore import firestore_service

logger = logging.getLogger(__name__)

router = APIRouter()


class UserSettings(BaseModel):
    """User settings model."""
    default_input_path: str = Field("input", alias="defaultInputPath")
    default_output_path: str = Field("output", alias="defaultOutputPath")
    default_output_format: str = Field("markdown", alias="defaultOutputFormat")
    email_notifications: bool = Field(True, alias="emailNotifications")
    theme: str = Field("system")

    class Config:
        populate_by_name = True


class UpdateSettingsRequest(BaseModel):
    """Request to update user settings."""
    default_input_path: Optional[str] = Field(None, alias="defaultInputPath")
    default_output_path: Optional[str] = Field(None, alias="defaultOutputPath")
    default_output_format: Optional[str] = Field(None, alias="defaultOutputFormat")
    email_notifications: Optional[bool] = Field(None, alias="emailNotifications")
    theme: Optional[str] = None

    class Config:
        populate_by_name = True


@router.get("/settings", response_model=UserSettings)
async def get_settings(
    current_user: dict = Depends(get_current_user),
):
    """Get user settings."""
    user_id = current_user["uid"]

    try:
        settings_data = await firestore_service.get_user_settings(user_id)

        if not settings_data:
            # Return defaults if no settings exist
            return UserSettings()

        return UserSettings(
            defaultInputPath=settings_data.get("default_input_path", "input"),
            defaultOutputPath=settings_data.get("default_output_path", "output"),
            defaultOutputFormat=settings_data.get("default_output_format", "markdown"),
            emailNotifications=settings_data.get("email_notifications", True),
            theme=settings_data.get("theme", "system"),
        )
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get settings")


@router.put("/settings", response_model=UserSettings)
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user settings."""
    user_id = current_user["uid"]

    try:
        # Get current settings
        current_settings = await firestore_service.get_user_settings(user_id) or {}

        # Update with new values
        update_data = {}
        if request.default_input_path is not None:
            update_data["default_input_path"] = request.default_input_path
        if request.default_output_path is not None:
            update_data["default_output_path"] = request.default_output_path
        if request.default_output_format is not None:
            update_data["default_output_format"] = request.default_output_format
        if request.email_notifications is not None:
            update_data["email_notifications"] = request.email_notifications
        if request.theme is not None:
            update_data["theme"] = request.theme

        # Merge with current settings
        merged_settings = {**current_settings, **update_data}

        # Save
        await firestore_service.update_user_settings(user_id, merged_settings)

        return UserSettings(
            defaultInputPath=merged_settings.get("default_input_path", "input"),
            defaultOutputPath=merged_settings.get("default_output_path", "output"),
            defaultOutputFormat=merged_settings.get("default_output_format", "markdown"),
            emailNotifications=merged_settings.get("email_notifications", True),
            theme=merged_settings.get("theme", "system"),
        )
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.get("/settings/defaults")
async def get_default_settings():
    """Get system default settings."""
    return {
        "defaultInputPath": "input",
        "defaultOutputPath": "output",
        "defaultOutputFormat": "markdown",
        "emailNotifications": True,
        "theme": "system",
        "supportedFormats": ["markdown", "json", "html", "dolma"],
        "maxUploadSize": 100 * 1024 * 1024,  # 100MB
        "maxFilesPerUpload": 50,
    }
