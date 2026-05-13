import enum
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from app.database import Base


class PipelineStatus(str, enum.Enum):
    IDLE = "idle"
    PLANNING = "planning"
    DISPATCHING = "dispatching"
    REVIEWING = "reviewing"
    TESTING = "testing"
    READY_TO_SUBMIT = "ready_to_submit"
    COMPLETED = "completed"
    FAILED = "failed"


# 合法转移
VALID_TRANSITIONS: dict[PipelineStatus, list[PipelineStatus]] = {
    PipelineStatus.IDLE: [PipelineStatus.PLANNING],
    PipelineStatus.PLANNING: [PipelineStatus.DISPATCHING, PipelineStatus.FAILED],
    PipelineStatus.DISPATCHING: [PipelineStatus.REVIEWING, PipelineStatus.PLANNING],
    PipelineStatus.REVIEWING: [
        PipelineStatus.TESTING,
        PipelineStatus.DISPATCHING,
        PipelineStatus.PLANNING,
    ],
    PipelineStatus.TESTING: [
        PipelineStatus.READY_TO_SUBMIT,
        PipelineStatus.FAILED,
        PipelineStatus.DISPATCHING,
    ],
    PipelineStatus.READY_TO_SUBMIT: [PipelineStatus.COMPLETED, PipelineStatus.DISPATCHING],
    PipelineStatus.FAILED: [
        PipelineStatus.PLANNING,
        PipelineStatus.DISPATCHING,
        PipelineStatus.TESTING,
    ],
    PipelineStatus.COMPLETED: [],
}


def can_transition(current: PipelineStatus, target: PipelineStatus) -> bool:
    return target in VALID_TRANSITIONS.get(current, [])


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    llm_provider_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("llm_providers.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=PipelineStatus.IDLE.value, index=True
    )
    repo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    repo_path: Mapped[str | None] = mapped_column(String(500))
    branch: Mapped[str | None] = mapped_column(String(200))
    plan_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    plan_result: Mapped[str | None] = mapped_column(Text)
    code_commit: Mapped[str | None] = mapped_column(String(64))
    code_diff: Mapped[str | None] = mapped_column(Text)
    review_result: Mapped[str | None] = mapped_column(Text)
    review_verdict: Mapped[str | None] = mapped_column(String(20))
    test_cases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # 关系
    task: Mapped["Task"] = relationship("Task", back_populates="pipelines")  # noqa: F821
    llm_provider: Mapped["LLMProvider | None"] = relationship("LLMProvider")  # noqa: F821
    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        "ChatMessage", back_populates="pipeline", cascade="all, delete-orphan"
    )
