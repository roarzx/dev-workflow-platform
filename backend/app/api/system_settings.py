import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas import success, error

logger = structlog.get_logger()
router = APIRouter(prefix="/settings", tags=["settings"])

# .env 文件路径
import os
from pathlib import Path
ENV_PATH = Path(os.getenv("ENV_FILE_PATH", ".env"))

# 敏感字段：返回时脱敏
SENSITIVE_KEYS = {"TAPD_API_TOKEN", "GITLAB_TOKEN", "CICD_TRIGGER_TOKEN",
                   "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
                   "DEEPSEEK_API_KEY", "MINIMAX_API_KEY", "APP_SECRET_KEY", "POSTGRES_PASSWORD"}


class SettingItem(BaseModel):
    key: str
    value: str
    masked: bool = False  # 标记是否被脱敏


class SettingsUpdate(BaseModel):
    settings: list[SettingItem]


def _read_env() -> list[SettingItem]:
    """读取 .env 文件，返回配置项列表"""
    items: list[SettingItem] = []
    if not ENV_PATH.exists():
        return items

    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            masked = key in SENSITIVE_KEYS
            if masked and value and value != "":
                display = value[:2] + "****" + value[-2:] if len(value) > 4 else "****"
            else:
                display = value
            items.append(SettingItem(key=key, value=display, masked=masked))

    return items


def _write_env(updates: dict[str, str]) -> list[SettingItem]:
    """更新 .env 文件中的指定 key，返回更新后的完整列表"""
    # 先读取现有内容为字典
    existing: dict[str, str] = {}
    lines: list[str] = []

    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                raw = line
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, _, val = stripped.partition("=")
                    existing[key.strip()] = val.strip()
                lines.append(raw)

    # 合并更新
    existing.update(updates)

    # 重建文件内容：保留注释和结构，更新值
    new_lines: list[str] = []
    written_keys: set[str] = set()

    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, _, _ = stripped.partition("=")
                    key = key.strip()
                    if key in existing:
                        new_lines.append(f"{key}={existing[key]}\n")
                        written_keys.add(key)
                    # 如果 key 不在 updates 里但也不在 existing 里，保留原行
                else:
                    new_lines.append(line)
                    # 跳过注释行和空行

    # 追加新增的 key（原 .env 中没有的）
    for key, value in updates.items():
        if key not in written_keys:
            new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    logger.info("settings.updated", keys=list(updates.keys()))

    # 重新加载 settings（清除 lru_cache）
    from app.config import get_settings
    get_settings.cache_clear()

    return _read_env()


@router.get("")
async def get_settings():
    """获取所有配置（敏感字段脱敏）"""
    items = _read_env()
    return success([item.model_dump() for item in items])


@router.post("")
async def update_settings(body: SettingsUpdate):
    """更新配置项"""
    # 读取当前配置（脱敏值），用于判断敏感字段是否已存在
    current = {item.key: item.value for item in _read_env()}

    # 构建更新字典（敏感字段为空时保留已有值）
    updates: dict[str, str] = {}
    for item in body.settings:
        # 敏感字段：空值且当前已有值（含脱敏标记）则跳过，不覆盖
        if item.key in SENSITIVE_KEYS and not item.value.strip() and "****" in current.get(item.key, ""):
            continue
        updates[item.key] = item.value

    if not updates:
        return error("EMPTY_SETTINGS", "没有需要更新的配置项")

    try:
        items = _write_env(updates)
        return success([item.model_dump() for item in items], "配置已保存")
    except Exception as e:
        logger.error("settings.update_failed", error=str(e))
        return error("SETTINGS_SAVE_FAILED", f"保存配置失败: {str(e)}")


class TAPDTestRequest(BaseModel):
    """测试 TAPD 连接请求（可选传入表单值，优先使用）"""
    api_token: str = Field(default="", description="Access Token")
    workspace_id: str = Field(default="", description="工作区 ID")
    api_url: str = Field(default="", description="API 地址")


@router.post("/test-tapd")
async def test_tapd_connection(body: TAPDTestRequest | None = None):
    """测试 TAPD 连接：验证 token 有效性 + workspace 权限，并返回 workspace 名称"""
    # 优先使用前端传入的值，否则从 .env 读取
    items = _read_env()
    config = {item.key: item.value for item in items}

    api_token = (body.api_token if body and body.api_token else config.get("TAPD_API_TOKEN", ""))
    workspace_id = (body.workspace_id if body and body.workspace_id else config.get("TAPD_WORKSPACE_ID", ""))
    api_url = (body.api_url if body and body.api_url else config.get("TAPD_API_URL", "https://api.tapd.cn"))

    if not workspace_id:
        return error("TAPD_INCOMPLETE", "请先填写 TAPD 工作区 ID（从项目 URL 中提取，如 tapd.cn/tapd_fe/12345678/ 中的数字）")

    if not api_token or "****" in api_token:
        return error("TAPD_INCOMPLETE", "请填写 Access Token，且不能是脱敏值")

    try:
        import httpx
        headers = {"Authorization": f"Bearer {api_token}"}
        client = httpx.AsyncClient(headers=headers, timeout=15.0)

        # 1. 验证 token 并查询 workspace 名称
        workspace_name = ""
        try:
            ws_resp = await client.get(
                f"{api_url}/workspaces/{workspace_id}",
            )
            if ws_resp.status_code == 200:
                ws_data = ws_resp.json()
                data_field = ws_data.get("data")
                if isinstance(data_field, dict):
                    ws_info = data_field.get("Workspace", {})
                    workspace_name = ws_info.get("name", "") if isinstance(ws_info, dict) else ""
                elif isinstance(data_field, list) and len(data_field) > 0:
                    ws_info = data_field[0].get("Workspace", {}) if isinstance(data_field[0], dict) else {}
                    workspace_name = ws_info.get("name", "") if isinstance(ws_info, dict) else ""
        except Exception:
            pass  # workspace 信息获取失败不影响主流程

        # 2. 验证 workspace 权限（尝试查一条需求）
        resp = await client.get(
            f"{api_url}/stories",
            params={"workspace_id": workspace_id, "limit": 1},
        )
        await client.aclose()

        if resp.status_code == 200:
            data = resp.json()
            data_field = data.get("data")
            if isinstance(data_field, dict):
                story_count = len(data_field.get("stories", []))
            elif isinstance(data_field, list):
                story_count = len(data_field)
            else:
                story_count = 0
            return success({
                "connected": True,
                "sample_count": story_count,
                "workspace_name": workspace_name,
            }, "TAPD 连接成功")
        else:
            return error("TAPD_AUTH_FAILED", f"TAPD 认证失败 (HTTP {resp.status_code})")
    except Exception as e:
        return error("TAPD_CONNECT_FAILED", f"TAPD 连接失败: {str(e)}")
