import asyncio
import aiohttp

from asyncio import Semaphore

from crawlers.cp_algo.parser import CPAlgoParser
from config import settings
from logging_utils import get_logger

MAX_POOL_SIZE = settings.crawlers.cp_algo.MAX_POOL_SIZE

semaphore = Semaphore(MAX_POOL_SIZE)
logger = get_logger(__name__)


async def get_markdown_from_url(session: aiohttp.ClientSession, url: str) -> str:
    async with semaphore:  # this limits request amounts by current semaphore value
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                raw_html = await response.text()
        except Exception as e:
            logger.exception(f"An error occurred on crawling URL='{url}': '{e}'")
            raise e
        try:
            return CPAlgoParser.parse(raw_html)
        except Exception as e:
            logger.exception(f"An unexpected error occurred when parsing html from URL='{url}': '{e}'")
            raise e


async def crawl(urls: list[str]):
    tasks = [asyncio.create_task(get_markdown_from_url(url)) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    exception_count = len([r for r in results if isinstance(r, Exception)])
    success_count = len(urls) - exception_count
    logger.info(f"Crawled batch of {len(urls)} URLs: {success_count} OK, {exception_count} failed")
    # TODO save to database here


# TODO: someway to find the URLs from CPAlgo
# maybe get from database
async def get_urls() -> list[str]:
    raise NotImplementedError


if __name__ == '__main__':
    urls = asyncio.run(get_urls())
    asyncio.run(crawl(urls))
