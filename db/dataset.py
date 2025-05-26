from datetime import datetime, timezone
from typing import Annotated
from sqlalchemy import Connection, Enum, TEXT, TIMESTAMP, VARCHAR, ForeignKey, UniqueConstraint, func, event, select
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    Mapper,
    mapped_column,
    Session,
)
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import DB
from db.enums import PageTypeEnum, URLCrawlerStatusEnum

datetime_default_now = Annotated[Mapped[datetime], mapped_column(TIMESTAMP, default=datetime.now(), server_default=func.now())]

SYNC_URL = "sqlite:///dataset.db"
ASYNC_URL = "sqlite+aiosqlite:///dataset.db"
BaseModel = declarative_base()

class URL(BaseModel):
    __tablename__ = "url"
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(VARCHAR(500))
    crawl_status: Mapped[URLCrawlerStatusEnum] = mapped_column(Enum(URLCrawlerStatusEnum), default=URLCrawlerStatusEnum.PENDING)
    created_at: Mapped[datetime_default_now]
    updated_at: Mapped[datetime_default_now]
    deleted_at: Mapped[datetime | None]

    __table_args__ = (UniqueConstraint("url", name="unique_url_key"),)

    @staticmethod
    async def get_or_create(url: str, session: AsyncSession) -> tuple["URL", bool]:
        """
        Retrieves url item, and if does not exist, create it. Does not commit.

        :return: URL item, boolean flag that is true if the item was just created
        """
        item = await session.scalar(select(URL).where(URL.url == url))
        if not item:
            item = URL(url=url)
            session.add(item)
            await session.flush()
            return item, True
        else:
            return item, False


class Page(BaseModel):
    __tablename__ = "page"
    id: Mapped[int] = mapped_column(primary_key=True)
    url_id: Mapped[int] = mapped_column(ForeignKey("url.id"))
    content: Mapped[str] = mapped_column(TEXT)
    page_type: Mapped[PageTypeEnum] = mapped_column(Enum(PageTypeEnum))  # cast to enum happens automatically but only on client code
    page_uuid: Mapped[str | None] = mapped_column(VARCHAR(500))
    """Optional string id"""
    created_at: Mapped[datetime_default_now]
    updated_at: Mapped[datetime_default_now]
    deleted_at: Mapped[datetime | None]


@event.listens_for(Page, "before_update")
@event.listens_for(URL, "before_update")
def refresh_updated_at(mapper: Mapper, conn: Connection, instance):
    # if any columns changed (not counting multi-valued columns/relationships)
    if(
        hasattr(instance, "updated_at")
    ):
        instance.updated_at = datetime.now(tz=timezone.utc)   # all timestamps are in UTC


DATASET = DB(SYNC_URL, ASYNC_URL, BaseModel)
