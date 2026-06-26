from dataclasses import dataclass
from datetime import datetime

from content.enums import CrawlerSourceEnum, ResourceCrawlerStatusEnum, PageCrawlerStatusEnum

@dataclass
class Page:
    url: str
    content: str | None
    tags: dict
    crawl_status: PageCrawlerStatusEnum
    checksum: str | None
    crawl_failure_reason: str | None = None
    deleted_at: datetime | None = None

@dataclass
class Resource:
    uri: str
    description: str | None
    crawl_status: ResourceCrawlerStatusEnum
    source: CrawlerSourceEnum
    pages: list[Page]
    deleted_at: datetime | None = None

