from content.db.db import KnowledgeDatabase
from content.db.entities import BaseModel
from content.enums import CrawlerSourceEnum, PageCrawlerStatusEnum, ResourceCrawlerStatusEnum
from crawlers.cp_algo.crawler import CPAlgorithmsCrawler
from crawlers.cp_algo.parser import CPAlgorithmsParser

def async_wrapper(fn):
    async def async_fn(*args, **kwargs):
        return fn(*args, **kwargs)
    return async_fn


async def test_crawl_1_page_directly(sqlite_db: KnowledgeDatabase, monkeypatch):
    monkeypatch.setattr(CPAlgorithmsParser, "parse_navigation_page", lambda _: [("https://cp-algorithms.com/data_structures/stack_queue_modification.html", "description 1")])
    monkeypatch.setattr(CPAlgorithmsCrawler, "fetch_and_parse_page", async_wrapper(lambda _, __: "content 1"))

    crawler = CPAlgorithmsCrawler()
    mock_db = KnowledgeDatabase(
        sync_url="sqlite:///test.db",
        async_url = "sqlite+aiosqlite:///test.db",
        base_model=BaseModel,
    )
    uri = await anext(crawler.next_uris(mock_db, limit=1))
    assert uri == "cpalgo/data_structures/stack_queue_modification"
    resource = await crawler.crawl(uri)
    print(resource)
    assert resource.uri == "cpalgo/data_structures/stack_queue_modification"
    assert resource.crawl_status == ResourceCrawlerStatusEnum.DONE
    assert resource.source == CrawlerSourceEnum.CPALGO
    assert len(resource.pages) == 1
    assert resource.pages[0].content == "content 1"
    assert resource.pages[0].tags == {"subject": "data_structures", "title": "stack_queue_modification"}
    assert resource.pages[0].crawl_status == PageCrawlerStatusEnum.DONE
