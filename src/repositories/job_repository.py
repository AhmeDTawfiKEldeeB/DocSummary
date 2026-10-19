import uuid
from datetime import datetime, timezone
from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from src.db.models import DocumentJob, JobStatus, PipelineType
except ModuleNotFoundError:
    from db.models import DocumentJob, JobStatus, PipelineType


class JobRepository:
    """
    Data access repository for DocumentJob entities.
    Performs data access and flushes changes to the session without committing,
    leaving transaction boundaries to the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _parse_uuid(job_id: Union[uuid.UUID, str]) -> Optional[uuid.UUID]:
        """Consistently validates and parses a UUID, returning None if invalid."""
        if isinstance(job_id, uuid.UUID):
            return job_id
        if not isinstance(job_id, str):
            return None
        try:
            return uuid.UUID(job_id)
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def _resolve_pipeline(pipeline: Union[PipelineType, str]) -> PipelineType:
        """Resolves string or PipelineType enum."""
        if isinstance(pipeline, PipelineType):
            return pipeline
        try:
            return PipelineType(str(pipeline).upper())
        except ValueError:
            raise ValueError(
                f"Invalid pipeline type '{pipeline}'. Must be one of {[p.value for p in PipelineType]}"
            )

    @staticmethod
    def _resolve_status(status: Union[JobStatus, str]) -> JobStatus:
        """Resolves string or JobStatus enum."""
        if isinstance(status, JobStatus):
            return status
        try:
            return JobStatus(str(status).upper())
        except ValueError:
            raise ValueError(
                f"Invalid job status '{status}'. Must be one of {[s.value for s in JobStatus]}"
            )

    async def create_job(
        self,
        filename: str,
        pipeline: Union[PipelineType, str],
        total_pages: int,
    ) -> DocumentJob:
        """
        Creates a new DocumentJob with status PENDING and flushes it to the session.
        Does not commit the transaction.
        """
        resolved_pipeline = self._resolve_pipeline(pipeline)
        job = DocumentJob(
            filename=filename,
            pipeline=resolved_pipeline,
            total_pages=total_pages,
            status=JobStatus.PENDING,
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: Union[uuid.UUID, str]) -> Optional[DocumentJob]:
        """
        Retrieves a DocumentJob by its UUID.
        Returns None if the UUID is invalid or the job does not exist.
        """
        parsed_id = self._parse_uuid(job_id)
        if parsed_id is None:
            return None

        stmt = select(DocumentJob).where(DocumentJob.id == parsed_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: Union[uuid.UUID, str],
        status: Union[JobStatus, str],
        summary_result: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[DocumentJob]:
        """
        Updates the job status and optionally summary_result or error_message.
        Ensures existing values are preserved if optional arguments are omitted (None).
        Flushes changes without committing. Returns None if job not found.
        """
        job = await self.get_job(job_id)
        if job is None:
            return None

        job.status = self._resolve_status(status)

        # Do not erase existing summary or error merely because an optional argument was omitted
        if summary_result is not None:
            job.summary_result = summary_result
        if error_message is not None:
            job.error_message = error_message

        job.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(job)
        return job
