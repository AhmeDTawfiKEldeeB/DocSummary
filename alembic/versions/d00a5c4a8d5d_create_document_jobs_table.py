"""create_document_jobs_table

Revision ID: d00a5c4a8d5d
Revises: 
Create Date: 2026-10-18 14:10:02.972062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd00a5c4a8d5d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='job_status_enum', native_enum=False),
            nullable=False,
            default='PENDING',
        ),
        sa.Column(
            'pipeline',
            sa.Enum('SMALL_DOC', 'LARGE_DOC', name='pipeline_type_enum', native_enum=False),
            nullable=False,
        ),
        sa.Column('total_pages', sa.Integer(), nullable=False, default=0),
        sa.Column('summary_result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_jobs_status'), 'document_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_document_jobs_pipeline'), 'document_jobs', ['pipeline'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_document_jobs_pipeline'), table_name='document_jobs')
    op.drop_index(op.f('ix_document_jobs_status'), table_name='document_jobs')
    op.drop_table('document_jobs')
