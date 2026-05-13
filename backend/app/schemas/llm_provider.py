from pydantic import BaseModel
from datetime import datetime


class LLMProviderCreate(BaseModel):
    name: str
    display_name: str
    model: str
    api_base: str | None = None
    is_default: bool = False
    config: dict = {}


class LLMProviderUpdate(BaseModel):
    display_name: str | None = None
    model: str | None = None
    api_base: str | None = None
    is_default: bool | None = None
    config: dict | None = None


class LLMProviderOut(BaseModel):
    id: int
    name: str
    display_name: str
    model: str
    api_base: str | None
    is_default: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
