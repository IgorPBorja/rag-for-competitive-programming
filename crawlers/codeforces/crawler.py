import aiohttp
import asyncio
import os
import re

from playwright._impl._errors import Error as MissingBrowserClientError
from playwright.async_api import async_playwright, Browser, Playwright
from typing import AsyncGenerator

from content.db.db import KnowledgeDatabase
from content.entities import Resource
from crawlers import Crawler, CrawlerSourceEnum


class Codeforces(Crawler):
    """
    Crawler for Codeforces problems with Editorials.

    URI pattern follows codeforces/problem/<CONTEST_ID>/<PROBLEM_LETTER> (e.g "2224/C2")
    or codeforces/editorial/<CONTEST_ID>/<PROBLEM_LETTER>
    """
    source = CrawlerSourceEnum.CODEFORCES
    LOCALE = "en"  # always enforce statements in English language
    USER_AGENT = "rag-for-competitive-programming/0.1 (local crawler probe)"
    HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

    def __init__(self, *args, **kwargs):
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def launch_playwright_headless_client(self, playwright_session: Playwright):
        # Launch a real browser (Chromium)
        try:
            browser = await playwright_session.chromium.launch(headless=True)
        except MissingBrowserClientError as e:
            print("Chrome headless client was not installed. Installing now... (running `playwright install`)")
            os.system("playwright install")
            browser = await playwright_session.chromium.launch(headless=True)
        return browser

    async def fetch(self, browser_session: Browser, url: str) -> str:
        page = await browser_session.new_page()
        # Navigate to the target site
        await page.goto(url)
        # Wait for the network to idle (allows JS security tokens to load)
        await page.wait_for_load_state('networkidle')
        # Extract the fully rendered HTML
        html_content = await page.content()
        return html_content

    async def crawl(self, uri: str) -> Resource:
        page_type, contest_id, problem_letter = uri.split("/")[-3:]
        if page_type == "problem":
            url = f"https://codeforces.com/problemset/problem/{contest_id}/{problem_letter}?locale=en"
        elif page_type == "editorial":
            raise NotImplementedError("Crawling of editorials not implemented")
        else:
            raise ValueError(f"Invalid page type in uri: {uri}")

        async with async_playwright() as playwright_ctx:
            browser = await self.launch_playwright_headless_client(playwright_ctx)
            return await self.fetch(browser, url)
        
    def next_uris(self, db: KnowledgeDatabase, limit: int | None = None) -> AsyncGenerator[str, None]:
        raise NotImplementedError("TODO")


if __name__ == "__main__":
    asyncio.run(Codeforces().crawl("codeforces/problem/4/A"))
