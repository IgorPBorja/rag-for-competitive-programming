"""Probe Codeforces statement and API endpoints.

Usage:
    uv run python scripts/probe_codeforces.py --contest 4
"""

from __future__ import annotations

import argparse
import asyncio
import json

import aiohttp
from bs4 import BeautifulSoup


USER_AGENT = "rag-for-competitive-programming/0.1 (local crawler probe)"


async def fetch(session: aiohttp.ClientSession, url: str) -> tuple[int, str, str]:
    async with session.get(url, allow_redirects=True) as response:
        return response.status, response.headers.get("Content-Type", ""), await response.text()


async def main(contest_id: int) -> None:
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        endpoints = {
            "problemset_problem": f"https://codeforces.com/problemset/problem/{contest_id}/A?locale=en",
            "contest_problems": f"https://codeforces.com/contest/{contest_id}/problems?locale=en",
            "api": "https://codeforces.com/api/problemset.problems?lang=en",
        }

        for name, url in endpoints.items():
            print(f"\n== {name} ==\n{url}")
            try:
                status, content_type, html = await fetch(session, url)
            except Exception as exc:
                print(f"request failed: {type(exc).__name__}: {exc}")
                continue

            print(f"status={status} content_type={content_type} bytes={len(html.encode())}")

            if name == "api":
                try:
                    payload = json.loads(html)
                    problems = payload.get("result", {}).get("problems", [])
                    matching = [
                        problem for problem in problems
                        if problem.get("contestId") == contest_id
                    ]
                    print(f"api_status={payload.get('status')} total_problems={len(problems)}")
                    print(f"matching_contest_problems={len(matching)}")
                    print(json.dumps(matching[:3], indent=2, ensure_ascii=False))
                except json.JSONDecodeError as exc:
                    print(f"invalid JSON: {exc}")
                continue

            soup = BeautifulSoup(html, "html.parser")
            statements = soup.select("div.problem-statement")
            print(f"problem_statement_blocks={len(statements)}")
            if statements:
                for statement in statements[:3]:
                    title = statement.select_one(".title")
                    print("---")
                    print(title.get_text(" ", strip=True) if title else "<no title>")
                    print(statement.get_text(" ", strip=True))
            else:
                print(f"body_prefix={soup.get_text(' ', strip=True)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contest", type=int, default=4)
    args = parser.parse_args()
    asyncio.run(main(args.contest))
