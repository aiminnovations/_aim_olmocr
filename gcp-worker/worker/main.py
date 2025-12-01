"""
Main worker entry point.

Pulls messages from Pub/Sub and processes PDFs using olmOCR.
Supports both Parasail API mode (serverless) and local GPU mode.
"""

import asyncio
import json
import logging
import signal
import subprocess
import sys
import time
from typing import Optional

from google.cloud import pubsub_v1

from .config import config, ProcessingMode
from .processor import OlmOCRProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VLLMServer:
    """Manager for local vLLM server process (GPU mode only)."""

    def __init__(self, model_name: str, port: int):
        self.model_name = model_name
        self.port = port
        self.process: Optional[subprocess.Popen] = None

    def start(self) -> None:
        """Start the vLLM server."""
        if config.vllm_url:
            logger.info(f"Using external vLLM server at {config.vllm_url}")
            return

        logger.info(f"Starting vLLM server for model {self.model_name} on port {self.port}")

        cmd = [
            sys.executable, "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model_name,
            "--port", str(self.port),
            "--gpu-memory-utilization", "0.9",
            "--max-model-len", "16384",
            "--trust-remote-code",
        ]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Wait for server to be ready
        logger.info("Waiting for vLLM server to start...")
        self._wait_for_ready()
        logger.info("vLLM server is ready")

    def _wait_for_ready(self, timeout: int = 300) -> None:
        """Wait for the vLLM server to be ready."""
        import urllib.request
        import urllib.error

        start_time = time.time()
        url = f"http://localhost:{self.port}/health"

        while time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, ConnectionRefusedError):
                pass

            # Check if process died
            if self.process and self.process.poll() is not None:
                raise RuntimeError("vLLM server process died during startup")

            time.sleep(5)

        raise RuntimeError(f"vLLM server did not start within {timeout} seconds")

    def stop(self) -> None:
        """Stop the vLLM server."""
        if self.process:
            logger.info("Stopping vLLM server")
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None


class Worker:
    """Pub/Sub message worker."""

    def __init__(self):
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(
            config.gcp_project_id,
            config.pubsub_subscription,
        )
        self.running = True
        self.vllm_server: Optional[VLLMServer] = None
        self.processor: Optional[OlmOCRProcessor] = None

    async def start(self) -> None:
        """Start the worker."""
        logger.info(f"Starting worker {config.worker_id}")
        logger.info(f"Processing mode: {config.processing_mode.value}")
        logger.info(f"Subscription: {self.subscription_path}")

        # Start vLLM server only in GPU mode
        if config.processing_mode == ProcessingMode.LOCAL_GPU:
            logger.info("GPU mode: Starting local vLLM server")
            self.vllm_server = VLLMServer(config.local_model_name, config.vllm_port)
            self.vllm_server.start()
        else:
            logger.info(f"Parasail API mode: Using {config.parasail_api_url}")
            logger.info(f"Model: {config.parasail_model}")

        # Initialize processor
        self.processor = OlmOCRProcessor()

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # Start processing messages
        await self._process_messages()

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signal."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def _process_messages(self) -> None:
        """Process messages from Pub/Sub."""
        logger.info("Starting to process messages")

        async with self.processor:
            while self.running:
                try:
                    # Pull messages
                    response = self.subscriber.pull(
                        request={
                            "subscription": self.subscription_path,
                            "max_messages": config.max_messages,
                        },
                        timeout=30,
                    )

                    if not response.received_messages:
                        continue

                    for message in response.received_messages:
                        try:
                            # Parse message data
                            data = json.loads(message.message.data.decode())
                            logger.info(f"Received job: {data.get('job_id')}")

                            # Process the job
                            await self.processor.process_job(data)

                            # Acknowledge the message
                            self.subscriber.acknowledge(
                                request={
                                    "subscription": self.subscription_path,
                                    "ack_ids": [message.ack_id],
                                }
                            )
                            logger.info(f"Job {data.get('job_id')} acknowledged")

                        except Exception as e:
                            logger.error(f"Error processing message: {e}", exc_info=True)
                            # Don't acknowledge - message will be redelivered
                            # Optionally, nack with delay
                            self.subscriber.modify_ack_deadline(
                                request={
                                    "subscription": self.subscription_path,
                                    "ack_ids": [message.ack_id],
                                    "ack_deadline_seconds": 60,  # Retry after 1 minute
                                }
                            )

                except Exception as e:
                    if self.running:
                        logger.error(f"Error pulling messages: {e}")
                        await asyncio.sleep(5)

        # Cleanup
        if self.vllm_server:
            self.vllm_server.stop()

        logger.info("Worker stopped")


def main():
    """Main entry point."""
    # Log configuration
    logger.info("=" * 60)
    logger.info("olmOCR Worker Starting")
    logger.info("=" * 60)
    logger.info(f"GCP Project: {config.gcp_project_id}")
    logger.info(f"GCS Bucket: {config.gcs_bucket}")
    logger.info(f"Processing Mode: {config.processing_mode.value}")
    if config.is_parasail_mode:
        logger.info(f"Parasail Model: {config.parasail_model}")
        logger.info(f"Parasail API: {config.parasail_api_url}")
    else:
        logger.info(f"Local Model: {config.local_model_name}")
    logger.info("=" * 60)

    worker = Worker()
    asyncio.run(worker.start())


if __name__ == "__main__":
    main()
