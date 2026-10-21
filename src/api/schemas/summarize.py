import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

try:
    from src.db.models import JobStatus, PipelineType
except ModuleNotFoundError:
    from db.models import JobStatus, PipelineType


class JobCreateResponse(BaseModel):
    """
    Response returned upon successfully uploading a PDF and enqueuing a summarization job.
    Returned with HTTP 202 Accepted.
    """
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status (PENDING)")
    pipeline: PipelineType = Field(..., description="Selected summarization pipeline (SMALL_DOC or LARGE_DOC)")
    total_pages: int = Field(..., description="Actual detected page count of the uploaded PDF")


class JobStatusResponse(BaseModel):
    """
    Response returned when querying the status and results of a summarization job.
    """
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current status: PENDING, PROCESSING, COMPLETED, or FAILED")
    summary: Optional[str] = Field(None, description="Generated document summary (available when COMPLETED)")
    error: Optional[str] = Field(None, description="Sanitized error description (available when FAILED)")
