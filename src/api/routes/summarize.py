import asyncio
import io
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
import pymupdf
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.summarize import JobCreateResponse, JobStatusResponse
from src.config.settings import settings
from src.db.models import JobStatus, PipelineType
from src.db.session import get_db
from src.infrastructure.storage import BaseFileStorage, get_storage
from src.repositories.job_repository import JobRepository
from src.services import determine_pipeline
from src.workers.tasks import process_large_doc_task, process_small_doc_task

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=settings.api_prefix,
    tags=["summarize"],
)


@router.post(
    "/summarize",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload PDF and queue document summarization job",
    description=(
        "Uploads a PDF document, detects its actual page count, assigns the appropriate "
        "pipeline (SMALL_DOC for <=15 pages, LARGE_DOC for >15 pages), persists the job, "
        "and dispatches a background worker task."
    ),
)
async def create_summarization_job(
    file: Annotated[UploadFile, File(description="PDF document to summarize")],
    session: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[BaseFileStorage, Depends(get_storage)],
) -> JobCreateResponse:
    """Uploads a PDF, creates a persistent job, and enqueues background summarization."""
    # 1. Filename & extension validation
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF documents (.pdf) are supported.",
        )

    # 2. Read content and validate size
    try:
        content = await file.read()
    except Exception as read_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {read_err}",
        )

    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    max_size = getattr(settings, "max_file_size_bytes", 50 * 1024 * 1024)
    if len(content) > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {max_mb}MB.",
        )

    # 3. Validate PDF readability and extract actual page count
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
        total_pages = len(doc)
        doc.close()
        if total_pages == 0:
            raise ValueError("PDF has 0 pages")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid or readable PDF document.",
        )

    # 4. Pipeline selection rule
    pipeline = determine_pipeline(total_pages)

    # 5. Save file securely into configured storage
    try:
        file_reference = storage.save_file(content, filename)
    except Exception as store_err:
        logger.error(f"Failed to save file to storage: {store_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded document.",
        )

    # 6. Create persistent job in PostgreSQL via JobRepository
    repo = JobRepository(session)
    job = await repo.create_job(
        filename=filename,
        pipeline=pipeline,
        total_pages=total_pages,
    )
    await session.commit()

    # 7. Dispatch Celery task with dispatch failure handling
    try:
        if pipeline == PipelineType.SMALL_DOC:
            process_small_doc_task.delay(str(job.id), file_reference)
        else:
            process_large_doc_task.delay(str(job.id), file_reference)
    except Exception as dispatch_err:
        logger.error(f"Failed to dispatch Celery task for job {job.id}: {dispatch_err}")
        # Transition job state to FAILED so it does not stay PENDING forever
        await repo.update_job_status(
            job.id,
            JobStatus.FAILED,
            error_message="Failed to enqueue background processing task. Please try again later.",
        )
        await session.commit()
        # Clean up stored file to prevent orphaned storage
        storage.delete_file(file_reference)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to queue document for processing. Please try again later.",
        )

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        pipeline=job.pipeline,
        total_pages=job.total_pages,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get summarization job status and result",
    description="Polls the current lifecycle status (PENDING, PROCESSING, COMPLETED, or FAILED) and summary result.",
)
async def get_job_status(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusResponse:
    """Retrieves the current status, summary result, or failure error for a job."""
    repo = JobRepository(session)
    job = await repo.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        summary=job.summary_result if job.status == JobStatus.COMPLETED else None,
        error=job.error_message if job.status == JobStatus.FAILED else None,
    )


@router.get(
    "/jobs/{job_id}/stream",
    summary="Stream summarization job status and result",
    description="Streams Server-Sent Events (SSE) yielding real-time status transitions and streamed summary tokens.",
)
async def stream_job_status(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Streams SSE events as the job transitions and yields summary tokens upon completion."""
    repo = JobRepository(session)
    job = await repo.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    async def event_generator():
        last_status = None
        max_duration = 300  # 5 minutes safety timeout
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < max_duration:
            await session.rollback()
            current_job = await repo.get_job(job_id)

            if not current_job:
                yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            if current_job.status != last_status:
                last_status = current_job.status
                yield f"event: status\ndata: {json.dumps({'status': current_job.status, 'pipeline': current_job.pipeline, 'total_pages': current_job.total_pages})}\n\n"

            if current_job.status == JobStatus.COMPLETED:
                summary = current_job.summary_result or ""
                # Stream the summary content in progressive token chunks
                chunk_size = 4
                words = summary.split(" ")
                for i in range(0, len(words), chunk_size):
                    chunk_text = " ".join(words[i : i + chunk_size])
                    if i + chunk_size < len(words):
                        chunk_text += " "
                    yield f"event: token\ndata: {json.dumps({'token': chunk_text})}\n\n"
                    await asyncio.sleep(0.02)

                yield f"event: done\ndata: {json.dumps({'status': 'COMPLETED', 'summary': summary})}\n\n"
                break

            elif current_job.status == JobStatus.FAILED:
                yield f"event: error\ndata: {json.dumps({'status': 'FAILED', 'error': current_job.error_message})}\n\n"
                break

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
