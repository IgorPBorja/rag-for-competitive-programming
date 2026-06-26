from abc import ABC, abstractmethod
from typing import AsyncGenerator

from content.db.db import KnowledgeDatabase
from content.db.sqlite import SQLITE_DB
from content.entities import Resource
from content.enums import CrawlerSourceEnum


class Crawler(ABC):
    source: CrawlerSourceEnum

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    async def crawl(self, uri: str) -> Resource:
        pass

    # TODO should this be separate from the crawler?
    @abstractmethod
    async def next_uris(self, db: KnowledgeDatabase, limit: int | None = None) -> AsyncGenerator[str, None]:
        pass
    