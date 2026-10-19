import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, Uuid, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

try:
    from src.db.session import Base
except ModuleNotFoundError:
    from db.session import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineType(str, enum.Enum):
    SMALL_DOC = "SMALL_DOC"
    LARGE_DOC = "LARGE_DOC"


class DocumentJob(Base):
    """
    ORM model representing a PDF summarization job lifecycle.
    """
    __tablename__ = "document_jobs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(
            JobStatus,
            name="job_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
        ),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )
    pipeline: Mapped[PipelineType] = mapped_column(
        SQLEnum(
            PipelineType,
            name="pipeline_type_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )
    total_pages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    summary_result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentJob id={self.id} filename='{self.filename}' "
            f"status={self.status.value if isinstance(self.status, JobStatus) else self.status} "
            f"pipeline={self.pipeline.value if isinstance(self.pipeline, PipelineType) else self.pipeline}>"
        )
