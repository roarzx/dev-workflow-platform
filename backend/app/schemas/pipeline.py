from pydantic import BaseModel
from datetime import datetime


class PipelineCreate(BaseModel):
    task_id: int
    llm_provider_id: int | None = None


class PipelineOut(BaseModel):
    id: int
    task_id: int
    llm_provider_id: int | None
    status: str
    repo_url: str
    repo_path: str | None
    branch: str | None
    plan_result: str | None
    code_commit: str | None
    review_result: str | None
    review_verdict: str | None
    error_message: str | None
    retry_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageOut(BaseModel):
    id: int
    pipeline_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str


class ConfirmPlanRequest(BaseModel):
    plan_summary: str


class RetryRequest(BaseModel):
    additional_context: str | None = None
