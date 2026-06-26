from datetime import datetime, timezone
from typing import Annotated, Any
from sqlalchemy import Connection, Enum, TEXT, TIMESTAMP, VARCHAR, ForeignKey, UniqueConstraint, func, event
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    Mapper,
    mapped_column,
    relationship,
)
from sqlalchemy.types import JSON

from content.entities import Resource, Page
from content.enums import CrawlerSourceEnum, ResourceCrawlerStatusEnum, PageCrawlerStatusEnum 

datetime_default_now = Annotated[Mapped[datetime], mapped_column(TIMESTAMP, default=datetime.now(), server_default=func.now())]

BaseModel = declarative_base()

class ResourceOrmEntity(BaseModel):
    __tablename__ = "resource"
    id: Mapped[int] = mapped_column(primary_key=True)
    uri: Mapped[str] = mapped_column(VARCHAR(500))
    description: Mapped[str | None] = mapped_column(TEXT)
    crawl_status: Mapped[ResourceCrawlerStatusEnum] = mapped_column(Enum(ResourceCrawlerStatusEnum), default=ResourceCrawlerStatusEnum.NOT_STARTED)
    source: Mapped[CrawlerSourceEnum]
    created_at: Mapped[datetime_default_now]
    updated_at: Mapped[datetime_default_now]
    deleted_at: Mapped[datetime | None]

    pages: Mapped[list["PageOrmEntity"]] = relationship(
        "PageOrmEntity",
        # NOTE: back_populates, used on both sides synchronizes relationships
        # so the `resource` attribute in Page will be synchronized with the `pages` attribute here
        # because of the `back_populates="resource"` here and `back_populates="pages"` there.
        back_populates="resource",
        # emits a highly optimized "SELECT ... FROM <child_table> WHERE <foreign_key> IN (<parent_id>)",
        # good for one-to-many like this one
        lazy="selectin",
    )

    # TODO we might need to drop this later
    __table_args__ = (UniqueConstraint("uri", name="unique_resource_uri"),)

    def to_entity(self) -> Resource:
        return Resource(
            uri=self.uri,
            description=self.description,
            crawl_status=self.crawl_status,
            source=self.source,
            deleted_at=self.deleted_at,
            pages=[page.to_entity() for page in self.pages],
        )


class PageOrmEntity(BaseModel):
    __tablename__ = "page"
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resource.id"))
    url: Mapped[str] = mapped_column(VARCHAR(500))
    content: Mapped[str | None] = mapped_column(TEXT)
    tags: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    crawl_status: Mapped[PageCrawlerStatusEnum] = mapped_column(Enum(PageCrawlerStatusEnum), default=PageCrawlerStatusEnum.NOT_STARTED)
    checksum: Mapped[str | None]
    crawl_failure_reason: Mapped[str | None] = mapped_column(TEXT)
    created_at: Mapped[datetime_default_now]
    updated_at: Mapped[datetime_default_now]
    deleted_at: Mapped[datetime | None]

    resource: Mapped[ResourceOrmEntity]
    resource: Mapped["PageOrmEntity"] = relationship(
        "ResourceOrmEntity",
        back_populates="pages",
        # good for many-to-one like this one
        lazy="joined",
    )

    @staticmethod
    def from_entity(page: Page, resource_id: int) -> "PageOrmEntity":
        return PageOrmEntity(
            resource_id=resource_id,
            url=page.url,
            content=page.content,
            tags=page.tags,
            crawl_status=page.crawl_status,
            checksum=page.checksum,
            crawl_failure_reason=page.crawl_failure_reason,
            deleted_at=page.deleted_at,
        )

    def to_entity(self) -> Page:
        return Page(
            url=self.url,
            content=self.content,
            tags=self.tags,
            crawl_status=self.crawl_status,
            checksum=self.checksum,
            crawl_failure_reason=self.crawl_failure_reason,
            deleted_at=self.deleted_at,
        )


@event.listens_for(Page, "before_update")
@event.listens_for(Resource, "before_update")
def refresh_updated_at(mapper: Mapper, conn: Connection, instance):
    # if any columns changed (not counting multi-valued columns/relationships)
    if(
        hasattr(instance, "updated_at")
    ):
        instance.updated_at = datetime.now(tz=timezone.utc)   # all timestamps are in UTC
