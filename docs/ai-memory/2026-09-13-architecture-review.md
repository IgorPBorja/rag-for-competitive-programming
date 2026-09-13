# Crawler architecture review

Reference commit: `db2425388d44fb78491d7eff471fcdd4b4d28094`

Most important issues:

1. Failed crawls are persisted as successful

`CPAlgorithmsCrawler.crawl()` correctly returns a `Resource` with `FAILED` status when fetching fails, but the controller unconditionally writes:

```python
resource.crawl_status = ResourceCrawlerStatusEnum.DONE
```

See [controller.py:43-48](/home/igor/projects/rag-for-competitive-programming/crawlers/controller.py:43).

The controller should persist the returned resource status and page data. Currently, a parser or HTTP failure can become a `DONE` resource containing a failed page.

2. Exceptions leave resources stuck in `QUEUED`

If `crawler.crawl()` raises unexpectedly, the controller only logs the exception. The database row remains `QUEUED` forever.

It should mark the resource as `FAILED`, store an error reason, and possibly record retry metadata.

3. Re-crawling a resource probably breaks page persistence

This assignment:

```python
resource.pages = [PageOrmEntity.from_entity(...) ...]
```

replaces the relationship, but the relationship does not define `cascade="all, delete-orphan"`. Existing pages may be detached and have their `resource_id` nulled, despite the column being non-nullable.

You need an explicit replacement strategy:

- delete/replace old pages transactionally;
- or upsert pages by a stable page identity;
- or add `cascade="all, delete-orphan"` and use it deliberately.

Because page URLs are intentionally not unique, pages also need an identity such as `page_kind`, `ordinal`, or a source-specific external key. Tags should not be the only way to distinguish statement/tutorial/implementation pages.

4. The timestamp definition is incorrect

In [entities.py:16](/home/igor/projects/rag-for-competitive-programming/content/db/entities.py:16):

```python
default=datetime.now()
```

is evaluated once when the module is imported, not once per row. Also, the update event is attached to the domain dataclasses `Page` and `Resource`, not the SQLAlchemy ORM entities, so it will not reliably update ORM timestamps.

Use `default=datetime.now` or a database default, and attach `onupdate` or SQLAlchemy mapper events to `ResourceOrmEntity` and `PageOrmEntity`.

5. The controller does not currently provide rate-limit protection

The semaphore limits concurrent requests, but does not limit request frequency, retry bursts, or per-host traffic. Since rate-limit avoidance is explicitly part of the controller’s responsibility, you will eventually need:

- request timeouts;
- retry policy with exponential backoff;
- per-host rate limiting;
- response-status handling;
- a reusable `aiohttp.ClientSession`.

Currently, each CP-Algorithms page creates a new HTTP session in [crawler.py:49](/home/igor/projects/rag-for-competitive-programming/crawlers/cp_algo/crawler.py:49).

6. Discovery and crawling are coupled

The `next_uris()` method is reasonable for a prototype, but conceptually it is a discovery/catalog component rather than the crawler itself. A cleaner long-term split would be:

```text
Source discoverer → resource identities
Crawler/fetcher   → resource identity to Resource
Controller        → scheduling, retries, persistence
```

This will help when Codeforces requires multiple discovery strategies, pagination, incremental updates, or problem-ID ranges.

7. The CP-Algorithms parser has production hazards

Notable problems in [parser.py](/home/igor/projects/rag-for-competitive-programming/crawlers/cp_algo/parser.py):

- `parse()` writes to `../../data/dbg_html` on every crawl. A clean deployment may not have that directory, causing otherwise successful crawls to fail.
- `found_h1` starts as `True`, so the “missing h1” validation never works.
- code blocks are only found among direct children of the article;
- code extraction ignores non-`span` text nodes;
- `clang-format` failures are ignored;
- parsing assumes every article has the expected structure.

The parser should be deterministic and side-effect-free. Debug dumping should be optional logging or an explicit test utility.

8. `next_uris()` will requeue everything every time

For CP-Algorithms, navigation-page enumeration is understandable, but every run upserts every URI as `QUEUED`, including already completed resources. That means a future scheduled crawl will recrawl the entire site.

The discoverer/controller should distinguish:

- never crawled;
- stale content;
- currently running;
- failed and eligible for retry;
- unchanged resources.

The checksum is a useful foundation for change detection, but it is currently only stored after fetching.

9. Status handling needs stronger semantics

`IN_PROGRESS` is defined but unused. A robust controller should atomically claim work, set `IN_PROGRESS`, and recover abandoned jobs after a timeout. Otherwise, process crashes can leave ambiguous state.

The `Resource | Exception` return convention also makes failure handling awkward. A typed crawl result containing status, pages, error, and retryability would be easier to reason about.

10. The tests are too dependent on the live network

The mocked integration test is useful, but the E2E tests make real requests and have no meaningful assertions. The combined test run timed out during the live network tests.

Add tests for:

- HTTP failure;
- parser failure;
- failed resource persistence;
- unexpected exception persistence;
- re-crawling the same resource;
- duplicate discovery results;
- timestamp updates;
- cancellation and retry behavior;
- parser input without an article or h1.

My recommended next step would be to stabilize the persistence boundary before implementing another source:

```text
discover URIs
→ atomically claim resources
→ crawl
→ persist resource status and pages in one transaction
→ retry or record failure
```

The domain model is pointed in the right direction, especially the decision to allow one resource to contain multiple pages. The main architectural adjustment is to make page identity, crawl state transitions, retries, and replacement/upsert semantics explicit.
