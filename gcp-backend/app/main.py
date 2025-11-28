"""
olmOCR GCP Backend API

FastAPI application for the olmOCR web interface.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import browse, upload, processing, download, settings as settings_router
from app.middleware.auth import AuthMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("Starting olmOCR API server...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"GCS Bucket: {settings.gcs_bucket}")

    yield

    # Shutdown
    logger.info("Shutting down olmOCR API server...")


# Create FastAPI app
app = FastAPI(
    title="olmOCR API",
    description="API for olmOCR PDF processing service",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(browse.router, prefix="/api/v1", tags=["Browse"])
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(processing.router, prefix="/api/v1", tags=["Processing"])
app.include_router(download.router, prefix="/api/v1", tags=["Download"])
app.include_router(settings_router.router, prefix="/api/v1", tags=["Settings"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "olmOCR API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.environment == "development",
    )
