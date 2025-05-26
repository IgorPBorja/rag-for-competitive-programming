from datetime import datetime, timezone
from typing import Annotated
from sqlalchemy import TEXT, TIMESTAMP, VARCHAR, ForeignKey, func, event
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column,
    Session,
)

from db.db import DB
from db.enums import PageTypeEnum, URLCrawlerStatusEnum

datetime_default_now = Annotated[Mapped[datetime], mapped_column(TIMESTAMP, default=datetime.now(), server_default=func.now())]

SYNC_URL = "sqlite:///dataset.db"
ASYNC_URL = "sqlite+aiosqlite:///dataset.db"
BaseModel = declarative_base()

class URL(BaseModel):
    __tablename__ = "url"
    id: Mapped[int]
    url: Mapped[str] = mapped_column(VARCHAR(500))
    crawl_status: Mapped[URLCrawlerStatusEnum] = mapped_column(VARCHAR(500))
    created_at: Mapped[datetime_default_now]
    updated_at: Mapped[datetime_default_now]
    deleted_at: Mapped[datetime | None]


class Page(BaseModel):
    __tablename__ = "page"
    id: Mapped[int]
    url_id: Mapped[int] = mapped_column(ForeignKey("url.id"))
    content: Mapped[str] = mapped_column(TEXT)
    page_type: Mapped[PageTypeEnum] = mapped_column(VARCHAR(500))  # cast to enum happens automatically but only on client code
    page_uuid: Mapped[str | None] = mapped_column(VARCHAR(500))
    """Optional string id"""
    created_at: Mapped[datetime_default_now]
    updated_at: Mapped[datetime_default_now]
    deleted_at: Mapped[datetime | None]


@event.listens_for(Page, "before_flush")
@event.listens_for(URL, "before_flush")
def refresh_updated_at(session: Session, flush_context, instances):
    for obj in session.dirty:
        # if any columns changed (not counting multi-valued columns/relationships)
        if (
            session.is_modified(obj, include_collections=False)
            and hasattr(obj, "updated_at")
        ):
            obj.updated_at = datetime.now(tz=timezone.utc)   # all timestamps are in UTC



dataset = DB(SYNC_URL, ASYNC_URL, BaseModel)
