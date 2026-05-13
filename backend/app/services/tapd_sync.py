import structlog
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.sync_cursor import SyncCursor
from app.models.sync_log import SyncLog
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class TAPDClient:
    """TAPD API 客户端封装（Access Token 认证）"""

    def __init__(self):
        import httpx
        self.base_url = settings.tapd_api_url
        self.workspace_id = settings.tapd_workspace_id
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {settings.tapd_api_token}"},
        )

    async def query_stories(self, modified_after: str | None = None) -> list[dict]:
        """查询 TAPD 需求（支持增量过滤）"""
        params = {
            "workspace_id": self.workspace_id,
            "fields": "id,name,description,status,priority,modified",
            "limit": 200,
        }
        if modified_after:
            params["modified"] = modified_after

        response = await self.client.get(
            f"{self.base_url}/stories",
            params=params,
        )
        response.raise_for_status()
        data = response.json()

        stories = []
        for item in data.get("data", {}).get("stories", []):
            story = item.get("Story", {})
            stories.append({
                "tapd_id": story.get("id", ""),
                "title": story.get("name", ""),
                "description": story.get("description", ""),
                "status": story.get("status", "open"),
                "priority": story.get("priority", ""),
                "tapd_url": f"{self.base_url.replace('/api', '')}/prong/stories/view/{self.workspace_id}/{story.get('id', '')}",
                "updated_at": self._parse_tapd_time(story.get("modified", "")),
            })
        return stories

    async def close(self):
        await self.client.aclose()

    @staticmethod
    def _parse_tapd_time(time_str: str) -> datetime | None:
        if not time_str:
            return None
        try:
            # TAPD 时间格式：2026-04-27T15:00:00+08:00
            return datetime.fromisoformat(time_str)
        except (ValueError, TypeError):
            return None


class TAPDSyncService:
    """TAPD 增量同步服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = TAPDClient()

    async def sync(self) -> dict:
        """执行增量同步"""
        stats = {"created": 0, "updated": 0, "skipped": 0}

        try:
            # 获取游标
            cursor_result = await self.db.execute(
                select(SyncCursor).where(SyncCursor.source == "tapd")
            )
            cursor = cursor_result.scalar_one_or_none()

            modified_after = cursor.cursor_value if cursor else None

            # 拉取数据
            items = await self.client.query_stories(modified_after=modified_after)

            for item in items:
                existing_result = await self.db.execute(
                    select(Task).where(Task.tapd_id == item["tapd_id"])
                )
                existing = existing_result.scalar_one_or_none()

                if existing and item["updated_at"] and item["updated_at"] <= existing.tapd_updated_at:
                    stats["skipped"] += 1
                    continue

                if existing:
                    existing.title = item["title"]
                    existing.description = item["description"]
                    existing.status = item["status"]
                    existing.priority = item["priority"]
                    existing.tapd_url = item["tapd_url"]
                    existing.tapd_updated_at = item["updated_at"]
                    existing.synced_at = datetime.now(timezone.utc)
                    existing.sync_version += 1
                    stats["updated"] += 1
                else:
                    task = Task(
                        tapd_id=item["tapd_id"],
                        title=item["title"],
                        description=item["description"],
                        status=item["status"],
                        priority=item["priority"],
                        tapd_url=item["tapd_url"],
                        tapd_updated_at=item["updated_at"],
                    )
                    self.db.add(task)
                    stats["created"] += 1

            # 更新游标
            latest_time = None
            for item in items:
                if item["updated_at"]:
                    if latest_time is None or item["updated_at"] > latest_time:
                        latest_time = item["updated_at"]

            if latest_time:
                if cursor:
                    cursor.cursor_value = latest_time.isoformat()
                    cursor.synced_at = datetime.now(timezone.utc)
                else:
                    new_cursor = SyncCursor(
                        source="tapd",
                        cursor_value=latest_time.isoformat(),
                    )
                    self.db.add(new_cursor)

            await self.db.commit()

            # 记录日志
            sync_log = SyncLog(
                source="tapd",
                action="sync",
                detail=f"增量同步完成：+{stats['created']} ~{stats['updated']} ={stats['skipped']}",
            )
            self.db.add(sync_log)
            await self.db.commit()

            logger.info("tapd.sync.completed", **stats)

        except Exception as e:
            await self.db.rollback()
            error_log = SyncLog(
                source="tapd",
                action="error",
                detail=f"同步失败: {str(e)}",
            )
            self.db.add(error_log)
            await self.db.commit()
            logger.error("tapd.sync.failed", error=str(e))
            raise
        finally:
            await self.client.close()

        return stats
