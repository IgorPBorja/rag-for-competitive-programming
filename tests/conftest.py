import os

from content.db.db import KnowledgeDatabase
from content.db.entities import BaseModel
import pytest


@pytest.fixture()
def sqlite_db():
    yield KnowledgeDatabase(
        sync_url="sqlite:///test.db",
        async_url = "sqlite+aiosqlite:///test.db",
        base_model=BaseModel,
    )
    # teardown
    os.remove("test.db")
