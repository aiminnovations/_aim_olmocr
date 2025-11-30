"""
HTTP handler for Cloud Run with Pub/Sub push subscription.

This module provides an HTTP server that receives Pub/Sub messages
via push subscription, suitable for Cloud Run deployment.
"""

import asyncio
import base64
import json
import logging
import os
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from .config import config
from .processor import OlmOCRProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="olmOCR Worker",
    description="Worker service for processing PDF OCR jobs",
    version="1.0.0",
)

# Global processor instance
processor: Optional[OlmOCRProcessor] = None


@app.on_event("startup")
async def startup():
    """Initialize processor on startup."""
    global processor
    logger.info("=" * 60)
    logger.info("olmOCR Worker Starting (HTTP mode)")
    logger.info("=" * 60)
    logger.info(f"GCP Project: {config.gcp_project_id}")
    logger.info(f"GCS Bucket: {config.gcs_bucket}")
    logger.info(f"Processing Mode: {config.processing_mode.value}")
    if config.is_parasail_mode:
        logger.info(f"Parasail Model: {config.parasail_model}")
        logger.info(f"Parasail API: {config.parasail_api_url}")
    logger.info("=" * 60)

    processor = OlmOCRProcessor()
    await processor.__aenter__()
    logger.info("Processor initialized")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    global processor
    if processor:
        await processor.__aexit__(None, None, None)
        logger.info("Processor shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "mode": config.processing_mode.value}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "olmOCR Worker",
        "version": "1.0.0",
        "mode": config.processing_mode.value,
    }


@app.post("/process")
async def process_pubsub_message(request: Request):
    """
    Process a Pub/Sub push message.

    Pub/Sub sends messages in the format:
    {
        "message": {
            "data": "<base64-encoded-json>",
            "messageId": "...",
            "publishTime": "..."
        },
        "subscription": "..."
    }
    """
    global processor

    if not processor:
        raise HTTPException(status_code=503, detail="Processor not initialized")

    try:
        # Parse Pub/Sub envelope
        envelope = await request.json()

        if not isinstance(envelope, dict) or "message" not in envelope:
            logger.error(f"Invalid Pub/Sub message format: {envelope}")
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        message = envelope["message"]
        message_id = message.get("messageId", "unknown")

        # Decode message data
        if "data" not in message:
            logger.error(f"No data in Pub/Sub message {message_id}")
            raise HTTPException(status_code=400, detail="No data in message")

        try:
            data_bytes = base64.b64decode(message["data"])
            job_data = json.loads(data_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to decode message data: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid message data: {e}")

        job_id = job_data.get("job_id", "unknown")
        logger.info(f"Received job {job_id} via Pub/Sub message {message_id}")

        # Process the job
        try:
            await processor.process_job(job_data)
            logger.info(f"Job {job_id} completed successfully")
            return JSONResponse(
                status_code=200,
                content={"status": "success", "job_id": job_id}
            )
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            # Return 500 to trigger Pub/Sub retry
            raise HTTPException(status_code=500, detail=f"Job processing failed: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/direct")
async def process_direct(request: Request):
    """
    Direct job submission endpoint (for testing).

    Expects job data directly in the request body.
    """
    global processor

    if not processor:
        raise HTTPException(status_code=503, detail="Processor not initialized")

    try:
        job_data = await request.json()
        job_id = job_data.get("job_id", "unknown")

        logger.info(f"Received direct job {job_id}")

        await processor.process_job(job_data)

        logger.info(f"Job {job_id} completed successfully")
        return JSONResponse(
            status_code=200,
            content={"status": "success", "job_id": job_id}
        )

    except Exception as e:
        logger.error(f"Error processing direct request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def run_server():
    """Run the HTTP server."""
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(
        "worker.http_handler:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    run_server()
