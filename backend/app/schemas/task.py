from pydantic import BaseModel
from datetime import datetime


class TaskBase(BaseModel):
    tapd_id: str
    title: str
    description: str | None = None
    status: str = "open"
    priority: str | None = None
    tapd_url: str | None = None


class TaskOut(BaseModel):
    id: int
    tapd_id: str
    title: str
    description: str | None
    status: str
    priority: str | None
    tapd_url: str | None
    synced_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    status: str | None = None


class TaskListParams(BaseModel):
    page: int = 1
    page_size: int = 20
    status: str | None = None
    priority: str | None = None
    sort: str = "synced_at"
    order: str = "desc"
