import asyncio
import aiohttp

from asyncio import Semaphore

from crawlers.cp_algo.parser import CPAlgoParser
from config import settings
from db.dataset import DATASET, URL, Page
from db.enums import PageTypeEnum, URLCrawlerStatusEnum
from logging_utils import get_logger

MAX_POOL_SIZE = settings.crawlers.cp_algo.MAX_POOL_SIZE

semaphore = Semaphore(MAX_POOL_SIZE)
logger = get_logger(__name__)


async def _get_markdown_from_url(url: str, session: aiohttp.ClientSession) -> tuple[str, str]:
    """
    Get markdown content from URL
    
    Returns original URL (acts as a task ID) and the markdown content
    Might raise Exception in the crawling or the parsing

    :retunrs: url and markdown content
    """
    async with semaphore:  # this limits request amounts by current semaphore value
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                raw_html = await response.text()
        except Exception as e:
            logger.exception(f"An error occurred on crawling URL='{url}': '{e}'")
            raise e
        try:
            return url, CPAlgoParser.parse(raw_html)
        except Exception as e:
            logger.exception(f"An unexpected error occurred when parsing html from URL='{url}': '{e}'")
            raise e


async def crawl(urls: list[str]):
    async with aiohttp.ClientSession() as http_session, DATASET.async_session() as db_session:
        urls = set(urls)  # force unique
        url_map = {}
        # queue URLs to crawl
        for url in urls:
            url_item, _ = await URL.get_or_create(url, db_session)
            url_item.crawl_status = URLCrawlerStatusEnum.QUEUED
            url_map[url] = url_item
        await db_session.commit()
        tasks = [asyncio.create_task(_get_markdown_from_url(url, http_session), name=url) for url in urls]

        success_count, exception_count = 0, 0
        for task in asyncio.as_completed(tasks):
            try:
                url, content = await task
            except Exception as e:
                logger.exception(f"Crawling {url=} went wrong: error '''{e}'''")
                exception_count += 1
            else:
                db_session.add(Page(
                    content=content,
                    url_id=url_map[url].id,
                    page_type=PageTypeEnum.CPALGO,
                    # page_uuid="cpalgo"  # TODO set uuid
                ))
                url_map[url].crawl_status = URLCrawlerStatusEnum.DONE
                success_count += 1
                await db_session.commit()
                logger.info(f"Crawled {url=} successfully")
        logger.info(f"Crawled total of {len(urls)} URLs: {success_count} OK, {exception_count} failed")


# TODO: someway to find the URLs from CPAlgo
# maybe get from database
async def get_urls() -> list[str]:
    NAVIGATION_URL = "https://cp-algorithms.com/navigation.html"
    async with aiohttp.ClientSession() as http_session:
        async with http_session.get(NAVIGATION_URL) as response:
            html_content = await response.text()
    links = CPAlgoParser.parse_navigation_page(html_content)
    async with DATASET.async_session() as db_session:
        # create links
        for link, description in links:
            await URL.get_or_create(link, db_session, description)
        await db_session.commit()
    return [url for url, _ in links]


if __name__ == '__main__':
    urls = asyncio.run(get_urls())
    asyncio.run(crawl(urls))
