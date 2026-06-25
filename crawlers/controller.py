import asyncio
import aiohttp

from content.db.db import KnowledgeDatabase
from content.db.entities import PageOrmEntity, ResourceOrmEntity
from content.enums import ResourceCrawlerStatusEnum
from crawlers import Crawler


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

    async def crawl(self, limit: int):
        """Crawls the next URIs
        and saves them on the database

        Args:
            limit (int): number of URIs/resources to crawl
        Returns:
            None
        """
        async with aiohttp.ClientSession() as http_session, self.db.async_session() as db_session:
            uri_to_resource_map = {}
            selected_uris = []
            async for uri in self.crawler.next_uris(db=self.db, limit=limit):
                # queue resources to crawl
                resouce = await self.db.upsert(ResourceOrmEntity, unique_columns=["uri"], params={"uri": uri, "source": self.crawler.source, "crawl_status": ResourceCrawlerStatusEnum.QUEUED}, session=db_session)
                uri_to_resource_map[uri] = resouce
                selected_uris.append(uri)
            await db_session.commit()
            tasks = [asyncio.create_task(self.crawler.crawl(uri), name=uri) for uri in selected_uris]

            # TODO fix this part!

            success_count, exception_count = 0, 0
            for task in asyncio.as_completed(tasks):
                try:
                    uri, content = await task
                except Exception as e:
                    logger.exception(f"Crawling {uri=} went wrong: error '''{e}'''")
                    exception_count += 1
                else:
                    # url is <BASE_URL>/section/
                    section_name = uri.removeprefix(BASE_URL + "/").removesuffix(".html")
                    db_session.add(PageOrmEntity(
                        content=content,
                        url_id=uri_to_resource_map[uri].id,
                        page_type=CrawlerSourceEnum.CPALGO,
                        page_uuid=f"cpalgo/{section_name}",
                    ))
                    uri_to_resource_map[uri].crawl_status = CrawlerStatusEnum.DONE
                    success_count += 1
                    await db_session.commit()
                    logger.info(f"Crawled {uri=} successfully")
            logger.info(f"Crawled total of {len(urls)} URLs: {success_count} OK, {exception_count} failed")