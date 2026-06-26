import asyncio
import aiohttp

from content.db.db import KnowledgeDatabase
from content.db.entities import PageOrmEntity, ResourceOrmEntity
from content.entities import Resource
from content.enums import ResourceCrawlerStatusEnum
from crawlers import Crawler
from logging_utils import get_logger
from sqlalchemy import select, update


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
        safe_future: asyncio.Future[tuple[str, Resource | Exception]],
        db: KnowledgeDatabase
    ) -> bool:
        """Handles a completed (successfully or not) task in the pool.
        If successful, adds the `Page` element, else logs the error

        :parameter safe_future (Future[tuple[str, Resource | Exception]]): the completed future
            It must return the uri back (so we can trace back to the original task)
            and be safe for execution (return the error instead of throwing)
        :returns status (bool): True if task was successful, else False
        """
        uri, result = await safe_future
        if isinstance(result, Exception):
            self.logger.exception(f"Crawling uri={uri} went wrong: error '''{result}'''")
            return False
        else:
            async with db.async_session() as session:
                resource = (await session.execute(select(ResourceOrmEntity).where(ResourceOrmEntity.uri == uri))).scalar_one()
                resource.pages = [PageOrmEntity.from_entity(page, resource_id=resource.id) for page in result.pages]
                resource.crawl_status = ResourceCrawlerStatusEnum.DONE
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
        async def safe_rate_limited_crawl_task(uri: str) -> tuple[str, Resource | Exception]:
            try:
                async with semaphore:
                    return uri, await self.crawler.crawl(uri)
            except Exception as e:
                return uri, e

        async with self.db.async_session() as db_session:
            uri_to_resource_map = {}
            selected_uris = []
            async for uri in self.crawler.next_uris(db=self.db, limit=limit):
                # queue resources to crawl
                resource = await self.db.upsert(ResourceOrmEntity, unique_columns=["uri"], params={"uri": uri, "source": self.crawler.source, "crawl_status": ResourceCrawlerStatusEnum.QUEUED}, session=db_session)
                uri_to_resource_map[uri] = resource
                selected_uris.append(uri)
            await db_session.commit()

            pending = [asyncio.create_task(safe_rate_limited_crawl_task(uri), name=uri) for uri in selected_uris]

            success_count, exception_count = 0, 0
            # https://stackoverflow.com/questions/50028465/python-get-reference-to-original-task-after-ordering-tasks-by-completion
            for future in asyncio.as_completed(pending):
                success = await self.handle_completed_crawl_task(safe_future=future, db=self.db)
                if success:
                    success_count += 1
                else:
                    exception_count += 1
            self.logger.info(f"Crawled total of {len(selected_uris)} resources: {success_count} OK, {exception_count} failed")
