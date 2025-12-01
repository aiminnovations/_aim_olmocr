"""
Worker configuration with support for both Parasail API and local GPU modes.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProcessingMode(Enum):
    """Processing mode for the worker."""
    PARASAIL = "parasail"  # Use Parasail API (serverless, pay-per-use)
    LOCAL_GPU = "local_gpu"  # Use local vLLM server with GPU


@dataclass
class WorkerConfig:
    """Worker configuration loaded from environment variables."""

    # GCP Settings
    gcp_project_id: str = field(default_factory=lambda: os.environ.get("GCP_PROJECT_ID", ""))
    gcs_bucket: str = field(default_factory=lambda: os.environ.get("GCS_BUCKET", ""))
    pubsub_subscription: str = field(default_factory=lambda: os.environ.get("PUBSUB_SUBSCRIPTION", "olmocr-jobs-sub"))

    # Processing mode
    processing_mode: ProcessingMode = field(default_factory=lambda: ProcessingMode(
        os.environ.get("PROCESSING_MODE", "parasail")
    ))

    # Parasail API settings (for API mode)
    parasail_api_key: str = field(default_factory=lambda: os.environ.get("PARASAIL_API_KEY", ""))
    parasail_api_url: str = field(default_factory=lambda: os.environ.get(
        "PARASAIL_API_URL", "https://api.parasail.io/v1/chat/completions"
    ))
    parasail_model: str = field(default_factory=lambda: os.environ.get(
        "PARASAIL_MODEL", "allenai/olmOCR-2-7B-1025"
    ))

    # Local GPU settings (for GPU mode)
    local_model_name: str = field(default_factory=lambda: os.environ.get(
        "MODEL_NAME", "allenai/olmOCR-2-7B-1025-FP8"
    ))
    vllm_port: int = field(default_factory=lambda: int(os.environ.get("VLLM_PORT", "30024")))
    vllm_url: Optional[str] = field(default_factory=lambda: os.environ.get("VLLM_URL"))

    # Processing settings (both modes)
    target_longest_image_dim: int = field(default_factory=lambda: int(
        os.environ.get("TARGET_LONGEST_IMAGE_DIM", "1288")
    ))
    max_page_retries: int = field(default_factory=lambda: int(os.environ.get("MAX_PAGE_RETRIES", "8")))
    max_concurrent_pages: int = field(default_factory=lambda: int(os.environ.get("MAX_CONCURRENT_PAGES", "10")))

    # Worker settings
    worker_id: str = field(default_factory=lambda: os.environ.get("HOSTNAME", "worker-0"))
    max_messages: int = field(default_factory=lambda: int(os.environ.get("MAX_MESSAGES", "1")))
    ack_deadline: int = field(default_factory=lambda: int(os.environ.get("ACK_DEADLINE", "600")))

    @property
    def is_parasail_mode(self) -> bool:
        """Check if using Parasail API mode."""
        return self.processing_mode == ProcessingMode.PARASAIL

    @property
    def model_name(self) -> str:
        """Get the model name based on processing mode."""
        if self.is_parasail_mode:
            return self.parasail_model
        return self.local_model_name

    @property
    def api_endpoint(self) -> str:
        """Get the API endpoint URL."""
        if self.is_parasail_mode:
            return self.parasail_api_url
        if self.vllm_url:
            return self.vllm_url
        return f"http://localhost:{self.vllm_port}/v1/chat/completions"

    @property
    def api_headers(self) -> dict:
        """Get API headers including authentication."""
        headers = {"Content-Type": "application/json"}
        if self.is_parasail_mode and self.parasail_api_key:
            headers["Authorization"] = f"Bearer {self.parasail_api_key}"
        return headers

    # Backwards compatibility
    @property
    def vllm_endpoint(self) -> str:
        """Deprecated: Use api_endpoint instead."""
        return self.api_endpoint


config = WorkerConfig()
