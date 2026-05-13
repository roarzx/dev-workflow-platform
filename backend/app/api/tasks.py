import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import get_settings
from app.models.task import Task
from app.models.sync_log import SyncLog
from app.schemas import success, error
from app.schemas.task import TaskOut, TaskUpdate

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter(tags=["tasks"])


@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    sort: str = Query("synced_at"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    """获取需求看板列表（分页）"""
    query = select(Task)

    # 筛选
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)

    # 计数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # 排序
    sort_col = getattr(Task, sort, Task.synced_at)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return success({
        "items": [TaskOut.model_validate(t) for t in tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    })


@router.post("/tasks/sync")
async def trigger_sync(db: AsyncSession = Depends(get_db)):
    """手动触发 TAPD 同步"""
    from app.services.tapd_sync import TAPDSyncService

    # 前置检查：TAPD 配置是否完整
    if not settings.tapd_workspace_id or settings.tapd_workspace_id == "your-workspace-id":
        return error("TAPD_NOT_CONFIGURED", "TAPD 未配置：请在设置页面中配置 TAPD 工作区 ID 和 Access Token")
    if not settings.tapd_api_token:
        return error("TAPD_NOT_CONFIGURED", "TAPD 未配置：请在设置页面中填写 Access Token")

    try:
        sync_service = TAPDSyncService(db)
        stats = await sync_service.sync()
        logger.info("tasks.sync_triggered", **stats)
        return success(stats, "同步完成")
    except Exception as e:
        logger.error("tasks.sync_failed", error=str(e))
        return error("SYNC_FAILED", f"TAPD 同步失败: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """获取需求详情"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "需求不存在"))
    return success(TaskOut.model_validate(task))


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新需求本地状态（有限字段）"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "需求不存在"))

    if body.status is not None:
        task.status = body.status

    await db.commit()
    await db.refresh(task)
    return success(TaskOut.model_validate(task))
