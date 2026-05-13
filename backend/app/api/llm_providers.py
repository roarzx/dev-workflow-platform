import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.llm_provider import LLMProvider
from app.schemas import success, error
from app.schemas.llm_provider import LLMProviderCreate, LLMProviderUpdate, LLMProviderOut

logger = structlog.get_logger()
router = APIRouter(tags=["llm-providers"])


@router.get("/llm-providers")
async def list_llm_providers(db: AsyncSession = Depends(get_db)):
    """获取 LLM 配置列表"""
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.created_at))
    providers = result.scalars().all()
    return success([LLMProviderOut.model_validate(p) for p in providers])


@router.post("/llm-providers", status_code=201)
async def create_llm_provider(body: LLMProviderCreate, db: AsyncSession = Depends(get_db)):
    """创建 LLM 配置"""
    # 如果设为默认，先取消其他默认
    if body.is_default:
        result = await db.execute(select(LLMProvider).where(LLMProvider.is_default == True))
        for p in result.scalars().all():
            p.is_default = False

    provider = LLMProvider(**body.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    logger.info("llm_provider.created", name=body.name, model=body.model)
    return success(LLMProviderOut.model_validate(provider))


@router.patch("/llm-providers/{provider_id}")
async def update_llm_provider(
    provider_id: int, body: LLMProviderUpdate, db: AsyncSession = Depends(get_db)
):
    """更新 LLM 配置"""
    provider = await db.get(LLMProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "LLM 配置不存在"))

    if body.is_default:
        result = await db.execute(select(LLMProvider).where(LLMProvider.is_default == True))
        for p in result.scalars().all():
            if p.id != provider_id:
                p.is_default = False

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)

    await db.commit()
    await db.refresh(provider)
    return success(LLMProviderOut.model_validate(provider))


@router.delete("/llm-providers/{provider_id}")
async def delete_llm_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    """删除 LLM 配置"""
    provider = await db.get(LLMProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=error("NOT_FOUND", "LLM 配置不存在"))

    await db.delete(provider)
    await db.commit()

    logger.info("llm_provider.deleted", provider_id=provider_id, name=provider.name)
    return success(message="已删除")
