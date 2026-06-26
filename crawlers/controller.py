import asyncio
import aiohttp

from content.db.db import KnowledgeDatabase
from content.db.entities import PageOrmEntity, ResourceOrmEntity
from content.entities import Resource
from content.enums import ResourceCrawlerStatusEnum
from crawlers import Crawler
from logging_utils import get_logger


class Controller:
    def __init__(
        self,
        crawler: Crawler,
        max_pool_size: int,
        db: KnowledgeDatabase,
    ):
        self.crawler = crawler
        self.max_pool_size = max_pool_size
        self.db = db
        self.logger = get_logger("crawler-controller")

    async def handle_completed_crawl_task(
        self,
        uri: str,
        result: asyncio.Future[Resource],
        db: KnowledgeDatabase
    ) -> bool:
        """Handles a completed (successfully or not) task in the pool.
        If successful, adds the `Page` element, else logs the error

        Returns:
            bool: True if task was successful, else False
        """
        try:
            resource = await result
        except Exception as e:
            self.logger.exception(f"Crawling uri={uri} went wrong: error '''{e}'''")
            exception_count += 1
            return False
        else:
            async with db.async_session() as session:
                await self.db.upsert(ResourceOrmEntity, unique_columns=["uri"], params={
                    "pages": [PageOrmEntity.from_entity(page) for page in resource.pages],
                    "crawl_status": ResourceCrawlerStatusEnum.DONE,
                })
            await session.commit()
            self.logger.info(f"Crawled uri={uri} successfully")
            return True

    async def crawl(self, limit: int):
        """Crawls the next URIs
        and saves them on the database

        Args:
            limit (int): number of URIs/resources to crawl
        Returns:
            None
        """
        semaphore = asyncio.Semaphore(self.max_pool_size)
        async def rate_limited_crawl_task(uri: str):
            async with semaphore:
                return await self.crawler.crawl(uri)

        async with self.db.async_session() as db_session:
            uri_to_resource_map = {}
            selected_uris = []
            async for uri in self.crawler.next_uris(db=self.db, limit=limit):
                # queue resources to crawl
                resouce = await self.db.upsert(ResourceOrmEntity, unique_columns=["uri"], params={"uri": uri, "source": self.crawler.source, "crawl_status": ResourceCrawlerStatusEnum.QUEUED}, session=db_session)
                uri_to_resource_map[uri] = resouce
                selected_uris.append(uri)
            await db_session.commit()

            tasks = [asyncio.create_task(rate_limited_crawl_task(uri), name=uri) for uri in selected_uris]

            success_count, exception_count = 0, 0
            for task in asyncio.as_completed(tasks):
                success = await self.handle_completed_crawl_task(uri=task.get_name(), result=task, db=self.db)
                if success:
                    success_count += 1
                else:
                    exception_count += 1
            self.logger.info(f"Crawled total of {len(selected_uris)} resources: {success_count} OK, {exception_count} failed")
