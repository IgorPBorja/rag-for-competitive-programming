import aiohttp

from hashlib import md5

from content.entities import Page, Resource
from crawlers import Crawler
from crawlers.cp_algo.parser import CPAlgoParser
from content.enums import CrawlerSourceEnum, PageCrawlerStatusEnum, ResourceCrawlerStatusEnum
from logging_utils import get_logger


class CPAlgorithmsCrawler(Crawler):
    """Crawler for the website https://cp-algorithms.com,
    which is a large collection of competitive-programming blogs and tutorials.

    Each URI follows this format:
    cpalgo/
    """
    source = CrawlerSourceEnum.CPALGO

    def __init__(self):
        self.logger = get_logger("cpalgo-crawler")

    @staticmethod
    def page_url_from_resource_uri(uri: str) -> str:
        path = uri.removeprefix("cpalgo/")
        return f"https://cp-algorithms.com/{path}.html"

    @staticmethod
    def tags_from_resource_uri(uri: str) -> dict[str]:
        path = uri.removeprefix("cpalgo/")
        path_components = path.split("/")
        subject = path_components[0]  # e.g "data_structures", "dynamic_programming"
        title = path_components[1]
        return {"subject": subject, "title": title}

    async def fetch_and_parse_page(self, url: str) -> str:
        """
        Get raw HTML content from URL, then parse it and extract
        the actual article as markdown.
        
        Returns original URL (acts as a task ID) and the markdown content
        Might raise Exception in the crawling or the parsing

        :param url (str): exact page URL, e.g https://cp-algorithms.com/data_structures/stack_queue_modification.html
        :returns content (str): markdown content
        """
        try:
            async with aiohttp.ClientSession() as http_session:
                async with http_session.get(url) as response:
                    response.raise_for_status()
                    raw_html = await response.text()
        except Exception as e:
            self.logger.exception(f"An error occurred on crawling URL='{url}': '{e}'")
            raise e
        try:
            return CPAlgoParser.parse(raw_html)
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred when parsing html from URL='{url}': '{e}'")
            raise e

    async def crawl(self, uri: str) -> Resource:
        page_url = self.page_url_from_resource_uri(uri)
        tags = self.tags_from_resource_uri(uri)
        try:
            content = await self.fetch_and_parse_page(page_url)
        except Exception as e:
            page = Page(
                url=page_url,
                content=None,
                tags=tags,
                crawl_status=PageCrawlerStatusEnum.FAILED,
                checksum=md5(content.encode("utf-8")).hexdigest(),
                crawl_failure_reason=str(e.with_traceback()),
            )
        else:
            page = Page(
                url=page_url,
                content=content,
                tags=tags,
                crawl_status=PageCrawlerStatusEnum.DONE,
                checksum=md5(content.encode("utf-8")).hexdigest(),
            )
        resource_status = ResourceCrawlerStatusEnum.DONE if page.crawl_status == PageCrawlerStatusEnum.DONE else ResourceCrawlerStatusEnum.FAILED
        return Resource(
            uri=uri,
            description="",  # TODO add description
            crawl_status=resource_status,
            source=self.source,
            pages=[page],
        )

    async def next_uris(self, db, limit = None):
        """Generates the next URIs to be searched

        In the case of CPAlgorithms there is no natural order to follow incrementally and the total number of pages is small, so we just crawl the navigation page and return all existing pages

        Yields:
            uri (str): resource identifier
        """
        NAVIGATION_URL = "https://cp-algorithms.com/navigation.html"
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(NAVIGATION_URL) as response:
                html_content = await response.text()
        links = CPAlgoParser.parse_navigation_page(html_content)
        # TODO figure out how to use this description (the underscore) somehow
        returned = 0
        for url, _ in links:
            path = url.removeprefix("https://cp-algorithms.com/").removesuffix(".html")
            uri = f"cpalgo/{path}"
            if limit is not None and returned >= limit:
                raise StopAsyncIteration
            else:
                yield uri
                returned += 1
