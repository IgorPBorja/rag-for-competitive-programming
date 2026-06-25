from enum import Enum

class CrawlerSourceEnum(Enum):
    CPALGO = "CPALGO"
    CODEFORCES = "CODEFORCES"

class ResourceCrawlerStatusEnum(Enum):
    NOT_STARTED = "NOT_STARTED"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"

class PageCrawlerStatusEnum(Enum):
    NOT_STARTED = "NOT_STARTED"
    QUEUED = "QUEUED"
    DONE = "DONE"
    FAILED = "FAILED"
