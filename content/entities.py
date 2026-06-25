from dataclasses import dataclass
from datetime import datetime

from content.enums import CrawlerSourceEnum, ResourceCrawlerStatusEnum, PageCrawlerStatusEnum

@dataclass
class Page:
    id: int
    resource_id: int
    url: str
    content: str | None
    tags: dict
    crawl_status: PageCrawlerStatusEnum
    checksum: str | None
    crawl_failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

@dataclass
class Resource:
    id: int
    uri: str
    description: str | None
    crawl_status: ResourceCrawlerStatusEnum
    source: CrawlerSourceEnum
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    pages: list[Page]

