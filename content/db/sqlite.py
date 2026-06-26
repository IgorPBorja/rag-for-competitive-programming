from content.db.db import KnowledgeDatabase
from content.db.entities import BaseModel


SYNC_URL = "sqlite:///dataset.db"
ASYNC_URL = "sqlite+aiosqlite:///dataset.db"
SQLITE_DB = KnowledgeDatabase(SYNC_URL, ASYNC_URL, BaseModel)