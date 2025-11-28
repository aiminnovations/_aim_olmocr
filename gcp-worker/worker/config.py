"""
Worker configuration.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkerConfig:
    """Worker configuration loaded from environment variables."""

    # GCP Settings
    gcp_project_id: str = os.environ.get("GCP_PROJECT_ID", "")
    gcs_bucket: str = os.environ.get("GCS_BUCKET", "")
    pubsub_subscription: str = os.environ.get("PUBSUB_SUBSCRIPTION", "olmocr-jobs-sub")

    # Model settings
    model_name: str = os.environ.get("MODEL_NAME", "allenai/olmOCR-2-7B-1025-FP8")
    vllm_port: int = int(os.environ.get("VLLM_PORT", "30024"))
    vllm_url: Optional[str] = os.environ.get("VLLM_URL")  # If external

    # Processing settings
    target_longest_image_dim: int = int(os.environ.get("TARGET_LONGEST_IMAGE_DIM", "1288"))
    max_page_retries: int = int(os.environ.get("MAX_PAGE_RETRIES", "8"))
    max_concurrent_pages: int = int(os.environ.get("MAX_CONCURRENT_PAGES", "10"))

    # Worker settings
    worker_id: str = os.environ.get("HOSTNAME", "worker-0")
    max_messages: int = int(os.environ.get("MAX_MESSAGES", "1"))  # Process one at a time
    ack_deadline: int = int(os.environ.get("ACK_DEADLINE", "600"))  # 10 minutes

    @property
    def vllm_endpoint(self) -> str:
        """Get vLLM endpoint URL."""
        if self.vllm_url:
            return self.vllm_url
        return f"http://localhost:{self.vllm_port}/v1/chat/completions"


config = WorkerConfig()
