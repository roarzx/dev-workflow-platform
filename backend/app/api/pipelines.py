import re
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import Task
from app.models.pipeline import PipelineRun, PipelineStatus, can_transition
from app.models.chat_message import ChatMessage
from app.schemas import success, error
from app.schemas.pipeline import (
    PipelineCreate, PipelineOut, ChatMessageOut,
    ChatRequest, ConfirmPlanRequest, RetryRequest,
)

logger = structlog.get_logger()
router = APIRouter(tags=["pipelines"])


def _generate_branch_name(tapd_id: str, title: str, pipeline_id: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]", "-", title[:20]).strip("-").lower()
    return f"feat/TAPD-{tapd_id}-{slug}-p{pipeline_id}"


@router.post("/pipelines", status_code=201)
async def create_pipeline(body: PipelineCreate, db: AsyncSession = Depends(get_db)):
    """创建管线实例"""
    task = await db.get(Task, body.task_id)
    if not task:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "需求不存在"))

    pipeline = PipelineRun(
        task_id=body.task_id,
        llm_provider_id=body.llm_provider_id,
        status=PipelineStatus.PLANNING.value,
        repo_url=task.tapd_url or "",
        plan_context={"task_title": task.title, "task_description": task.description},
    )
    db.add(pipeline)
    await db.flush()

    pipeline.branch = _generate_branch_name(task.tapd_id, task.title, pipeline.id)
    await db.commit()
    await db.refresh(pipeline)

    logger.info("pipeline.created", pipeline_id=pipeline.id, task_id=body.task_id)
    return success(PipelineOut.model_validate(pipeline))


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db)):
    """查询管线状态"""
    pipeline = await db.get(PipelineRun, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "管线不存在"))
    return success(PipelineOut.model_validate(pipeline))


@router.post("/pipelines/{pipeline_id}/chat")
async def chat(pipeline_id: int, body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """发送 AI 对话消息"""
    pipeline = await db.get(PipelineRun, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "管线不存在"))

    if pipeline.status != PipelineStatus.PLANNING.value:
        return error("INVALID_STATE", f"当前状态 {pipeline.status} 不支持对话，仅在 planning 阶段可讨论方案")

    # Phase 2 实现：调用 AI 编排服务
    # 目前先记录消息并返回占位回复
    user_msg = ChatMessage(pipeline_id=pipeline_id, role="user", content=body.message)
    db.add(user_msg)

    assistant_msg = ChatMessage(
        pipeline_id=pipeline_id,
        role="assistant",
        content="[Phase 2] AI 对话功能将在 Phase 2 集成 LangChain 后实现。当前消息已记录。",
    )
    db.add(assistant_msg)
    await db.commit()

    return success({
        "reply": assistant_msg.content,
        "status": pipeline.status,
        "message_id": assistant_msg.id,
    })


@router.post("/pipelines/{pipeline_id}/confirm-plan")
async def confirm_plan(
    pipeline_id: int, body: ConfirmPlanRequest, db: AsyncSession = Depends(get_db)
):
    """确认方案（触发代码生成）"""
    pipeline = await db.get(PipelineRun, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "管线不存在"))

    current = PipelineStatus(pipeline.status)
    target = PipelineStatus.DISPATCHING
    if not can_transition(current, target):
        return error("PIPELINE_INVALID_TRANSITION",
                     f"无法从 {current.value} 转移到 {target.value}")

    pipeline.plan_result = body.plan_summary
    pipeline.status = target.value
    await db.commit()

    logger.info("pipeline.plan_confirmed", pipeline_id=pipeline_id)
    return success({
        "pipeline_id": pipeline_id,
        "status": pipeline.status,
        "message": "方案已确认，代码生成任务已入队（Phase 3 实现实际调用 Claude Code）",
    })


@router.post("/pipelines/{pipeline_id}/start-review")
async def start_review(pipeline_id: int, db: AsyncSession = Depends(get_db)):
    """触发 AI 代码审查"""
    pipeline = await db.get(PipelineRun, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "管线不存在"))

    current = PipelineStatus(pipeline.status)
    if current != PipelineStatus.REVIEWING:
        return error("INVALID_STATE", f"当前状态 {current.value} 不支持审查，需先完成代码生成")

    # Phase 3 实现
    return success({
        "pipeline_id": pipeline_id,
        "status": pipeline.status,
        "message": "代码审查将在 Phase 3 实现",
    })


@router.post("/pipelines/{pipeline_id}/generate-tests")
async def generate_tests(pipeline_id: int, db: AsyncSession = Depends(get_db)):
    """生成测试用例"""
    pipeline = await db.get(PipelineRun, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "管线不存在"))

    # Phase 3 实现
    return success({
        "pipeline_id": pipeline_id,
        "status": pipeline.status,
        "message": "测试用例生成将在 Phase 3 实现",
    })


@router.post("/pipelines/{pipeline_id}/deploy")
async def deploy(pipeline_id: int, db: AsyncSession = Depends(get_db)):
    """触发测试环境部署"""
    pipeline = await db.get(PipelineRun, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "管线不存在"))

    current = PipelineStatus(pipeline.status)
    target = PipelineStatus.TESTING
    if not can_transition(current, target):
        return error("PIPELINE_INVALID_TRANSITION",
                     f"无法从 {current.value} 转移到 {target.value}")

    pipeline.status = target.value
    await db.commit()

    # Phase 3 实现：实际调用 CI/CD
    return success({
        "pipeline_id": pipeline_id,
        "status": pipeline.status,
        "message": "部署请求已发送（Phase 3 实现实际 CI/CD 调用）",
    })


@router.post("/pipelines/{pipeline_id}/retry")
async def retry_pipeline(
    pipeline_id: int, body: RetryRequest, db: AsyncSession = Depends(get_db)
):
    """重试当前失败步骤"""
    pipeline = await db.get(PipelineRun, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "管线不存在"))

    current = PipelineStatus(pipeline.status)
    if current not in (PipelineStatus.FAILED, PipelineStatus.PLANNING):
        return error("INVALID_STATE", f"当前状态 {current.value} 不支持重试")

    # 根据错误来源决定回退状态
    pipeline.status = PipelineStatus.PLANNING.value
    pipeline.retry_count += 1
    if body.additional_context:
        pipeline.error_message = body.additional_context

    await db.commit()
    return success({
        "pipeline_id": pipeline_id,
        "status": pipeline.status,
        "retry_count": pipeline.retry_count,
    })


@router.post("/pipelines/{pipeline_id}/submit")
async def submit_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db)):
    """提测（更新 TAPD）"""
    pipeline = await db.get(PipelineRun, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "管线不存在"))

    current = PipelineStatus(pipeline.status)
    target = PipelineStatus.COMPLETED
    if not can_transition(current, target):
        return error("PIPELINE_INVALID_TRANSITION",
                     f"无法从 {current.value} 转移到 {target.value}")

    pipeline.status = target.value
    pipeline.completed_at = func.now()
    await db.commit()

    # Phase 3 实现：实际更新 TAPD 状态
    logger.info("pipeline.submitted", pipeline_id=pipeline_id)
    return success({
        "pipeline_id": pipeline_id,
        "status": pipeline.status,
        "message": "已提测（Phase 3 实现实际 TAPD 更新）",
    })


# 修复缺失的 import
from sqlalchemy import func  # noqa: E402
