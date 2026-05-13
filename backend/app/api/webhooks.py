import structlog
from fastapi import APIRouter, Request

from app.schemas import success, error
from app.models.pipeline import PipelineStatus

logger = structlog.get_logger()
router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/cicd/{provider}")
async def handle_cicd_webhook(provider: str, request: Request):
    """接收 CI/CD 平台的部署状态回调"""
    payload = await request.json()
    logger.info("webhook.cicd.received", provider=provider, payload=payload)

    # Phase 3 实现：解析 payload，通过分支名反查管线，更新状态
    return success({"status": "received", "provider": provider})
