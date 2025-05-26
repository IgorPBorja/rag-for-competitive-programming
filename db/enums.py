from enum import Enum

class PageTypeEnum(Enum):
    CPALGO = "CPALGO"
    CODEFORCES_EDITORIAL = "CODEFORCES_EDITORIAL"

class URLCrawlerStatusEnum(Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    DONE = "DONE"
