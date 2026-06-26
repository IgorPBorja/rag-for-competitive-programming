from content.db.db import KnowledgeDatabase
from content.db.entities import BaseModel
from content.entities import Resource
from content.enums import CrawlerSourceEnum, PageCrawlerStatusEnum, ResourceCrawlerStatusEnum
from crawlers.controller import Controller
from crawlers.cp_algo.crawler import CPAlgorithmsCrawler
from crawlers.cp_algo.parser import CPAlgorithmsParser
from sqlalchemy import select


async def test_crawl_1_page_directly(sqlite_db: KnowledgeDatabase):
    crawler = CPAlgorithmsCrawler()
    uri = await anext(crawler.next_uris(sqlite_db, limit=1))
    print(f"first URI={uri}")
    resource = await crawler.crawl(uri)
    print(f"Resource = \n\n{resource.pages[0].content}")


async def test_crawl_1_page_through_controller(sqlite_db: KnowledgeDatabase):
    controller = Controller(crawler=CPAlgorithmsCrawler(), max_pool_size=10, db=sqlite_db)
    await controller.crawl(1)

    async with sqlite_db.async_session() as session:
        resource = await session.execute(select(Resource)).scalar_one()
    print(resource)
    print(f"Resource = \n\n{resource.pages[0].content}")
