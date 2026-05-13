import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import engine, Base

logger = structlog.get_logger()
settings = get_settings()

# 设置 .env 文件的绝对路径（供 settings API 使用）
import os
os.environ.setdefault("ENV_FILE_PATH", os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化资源，关闭时清理"""
    logger.info("app.starting", env=settings.app_env)

    # 开发环境下自动建表（生产环境用 Alembic）
    if settings.app_env == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db.tables_created")

    yield

    logger.info("app.shutting_down")
    await engine.dispose()


app = FastAPI(
    title="Dev Workflow Platform",
    description="个人开发工作流自动化平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 统一异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("app.unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "Internal server error", "detail": None},
    )


# 路由注册
from app.api import tasks, pipelines, llm_providers, webhooks, system_settings  # noqa: E402

app.include_router(tasks.router, prefix="/api/v1")
app.include_router(pipelines.router, prefix="/api/v1")
app.include_router(llm_providers.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(system_settings.router, prefix="/api/v1")


# 健康检查
@app.get("/api/v1/health")
async def health_check():
    return {"code": 0, "data": {"status": "ok"}, "message": "success"}
