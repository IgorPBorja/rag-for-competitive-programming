# Crawlers architecture

* Every crawler should be a self-contained module following the common interface below

```python
class Crawler:
    source: CrawlerSourceEnum

    def __init__(*args, **kwargs): ...

    # Returns the raw crawled content and arbitrary metadata in JSON format
    # The uri is an unique resource identification and
    # does not necesarily need to map to a single URL.
    # For example
    async def crawl(self, uri: str) -> Resource: ...
```

The `Resource` will be the persisted entity (before commit possibly, since commits can happen in batches) and will have the `Resource 1:---N: Page` relationships already loaded in.

Notice that every resource can point to **one or more items of content (here called pages)**:

* A blog post from CPAlgorithms only points to the blog post page
* A Codeforces problem can point to the statement, the tutorial and the implementation (editorial is split into tutorial and implementation)
* An AtCoder problem can point to the statement and the problem's editorial

# Database modelling

The database should contain the following tables:

```
resource
| ---> id (int, auto-incrementing)
| ---> uri (str)
| ---> description (str | None)
| ---> crawl_status ("NOT_STARTED" | "IN_PROGRESS" | "DONE" | "FAILED")
| ---> source (CrawlerSourceEnum)
| ---> created_at / updated_at / deleted_at

page
| ---> id (int, auto-incrementing)
| ---> resource_id (FK)
| ---> url (str)
| ---> content (str, large `TEXT` type)
| ---> tags (dict)
| ---> crawl_status ("NOT_STARTED" | "QUEUED" | "DONE" | "FAILED")
| ---> checksum (str | None)
| ---> crawl_failure_reason (str | None)
| ---> created_at / updated_at / deleted_at
```

About the status for resource crawling:
* 

Having sequential, auto-incrementing ids is fine because these are internal tables. The uri should be unique but that is not imposed as a hard requirement for now. Also **the URL in the page entity might not be unique, since the same URL in Codeforces can have the editorials for multiple problems**

# URL Generator 

* Generates the next URLs
* Might have a different strategy per source (re-generate everything, keep going from the last ID, etc)
    - Has to take the DB as a parameter, in order to query this kind of information

# Crawler controller

* Keeps a queue and a request pool and manages what needs to be crawled and when
* **Responsible for avoiding rate limits**


# References and cool links

* [Mercator architecture for Web Crawlers](https://medium.com/@kslohith1729/mercator-a-masterclass-in-system-design-for-a-web-crawler-30e690a9103b)