"""
Processing job models.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


JobStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
OutputFormat = Literal["markdown", "json", "html", "dolma"]


class JobProgress(BaseModel):
    """Job processing progress."""
    current: int = 0
    total: int = 0
    percentage: int = 0


class JobInput(BaseModel):
    """Job input file information."""
    path: str
    file_name: str = Field(..., alias="fileName")
    file_size: int = Field(..., alias="fileSize")
    page_count: int = Field(0, alias="pageCount")


class JobOutputFile(BaseModel):
    """Output file information."""
    name: str
    path: str
    size: int


class JobOutput(BaseModel):
    """Job output configuration."""
    path: str
    format: OutputFormat
    files: List[JobOutputFile] = []


class JobMetrics(BaseModel):
    """Job processing metrics."""
    input_tokens: int = Field(0, alias="inputTokens")
    output_tokens: int = Field(0, alias="outputTokens")
    processing_time_ms: int = Field(0, alias="processingTimeMs")


class Job(BaseModel):
    """Processing job model."""
    id: str
    user_id: str = Field(..., alias="userId")
    status: JobStatus = "pending"
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")
    input: JobInput
    output: JobOutput
    progress: JobProgress = JobProgress()
    metrics: Optional[JobMetrics] = None
    error: Optional[str] = None

    class Config:
        populate_by_name = True


class CreateJobOptions(BaseModel):
    """Options for job creation."""
    include_metadata: bool = Field(True, alias="includeMetadata")
    preserve_folder_structure: bool = Field(True, alias="preserveFolderStructure")
    language_filter: Optional[List[str]] = Field(None, alias="languageFilter")


class CreateJobRequest(BaseModel):
    """Request to create a processing job."""
    input_path: str = Field(..., alias="inputPath", min_length=1, max_length=500)
    output_path: str = Field(..., alias="outputPath", min_length=1, max_length=500)
    output_format: OutputFormat = Field("markdown", alias="outputFormat")
    options: Optional[CreateJobOptions] = None


class JobListResponse(BaseModel):
    """Response for job listing."""
    jobs: List[Job]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    total_pages: int = Field(..., alias="totalPages")

    class Config:
        populate_by_name = True
