"""
Authentication middleware using Firebase Admin SDK.
"""

import logging
import os
from typing import Optional

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
_firebase_app = None


def get_firebase_app():
    """Get or initialize Firebase Admin app."""
    global _firebase_app

    if _firebase_app is None:
        try:
            # Try to use credentials file
            if settings.firebase_credentials_path and os.path.exists(
                settings.firebase_credentials_path
            ):
                cred = credentials.Certificate(settings.firebase_credentials_path)
                _firebase_app = firebase_admin.initialize_app(cred)
            else:
                # Use Application Default Credentials (for Cloud Run)
                _firebase_app = firebase_admin.initialize_app()

            logger.info("Firebase Admin SDK initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise

    return _firebase_app


# HTTP Bearer token security
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Verify Firebase ID token and return user info.

    Returns:
        dict with user info including 'uid', 'email', etc.

    Raises:
        HTTPException 401 if token is invalid or missing
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Ensure Firebase is initialized
        get_firebase_app()

        # Verify the token
        decoded_token = auth.verify_id_token(token)

        # Store user info in request state
        request.state.user_id = decoded_token["uid"]
        request.state.user_email = decoded_token.get("email")

        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        raise HTTPException(
            status_code=401,
            detail="Failed to verify authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Optionally verify Firebase ID token.

    Returns user info if valid token provided, None otherwise.
    Does not raise exceptions for missing/invalid tokens.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


class AuthMiddleware:
    """
    Middleware for authentication (if needed for all routes).

    Note: For most cases, use Depends(get_current_user) instead.
    """

    async def __call__(self, request: Request, call_next):
        # Skip authentication for certain paths
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/"]

        if request.url.path in skip_paths:
            return await call_next(request)

        # For API routes, authentication is handled by dependencies
        return await call_next(request)
