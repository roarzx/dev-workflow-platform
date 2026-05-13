from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 应用
    app_env: str = "development"
    app_port: int = 8000
    app_secret_key: str = "change-me"
    api_key: str = "dev-api-key"

    # 数据库
    database_url: str = "postgresql+asyncpg://devwf:devwf_secret@localhost:5432/dev_workflow"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # TAPD
    tapd_api_url: str = "https://api.tapd.cn"
    tapd_api_token: str = ""
    tapd_workspace_id: str = ""
    tapd_sync_interval: int = 300

    # GitLab
    gitlab_url: str = ""
    gitlab_token: str = ""
    gitlab_default_base_path: str = "/data/repos"

    # Claude Code
    claude_code_timeout: int = 600

    # CI/CD
    cicd_provider: str = "gitlab"
    cicd_trigger_url: str = ""
    cicd_trigger_token: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
