from pydantic import BaseModel, Field
from typing import Any


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    code: int | str = 0
    data: Any = None
    message: str = "success"


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Any = None


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    has_more: bool


def success(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "data": data, "message": message}


def error(code: str, message: str, detail: Any = None) -> dict:
    return {"code": code, "message": message, "detail": detail}
