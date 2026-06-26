from content.db.db import KnowledgeDatabase
from content.db.entities import BaseModel
from crawlers.cp_algo.crawler import CPAlgorithmsCrawler


async def test_crawl_1_page_directly():
    crawler = CPAlgorithmsCrawler()
    DB = KnowledgeDatabase(
        sync_url="sqlite:///test.db",
        async_url = "sqlite+aiosqlite:///test.db",
        base_model=BaseModel,
    )
    uri = anext(crawler.next_uris(DB, limit=1))
    print(f"first URI={uri}")
    resource = await crawler.crawl(uri)
    print(f"Resource = \n\n{resource.content}")
