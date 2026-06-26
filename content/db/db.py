from contextlib import contextmanager, asynccontextmanager
from typing import Any, AsyncIterator, Iterator
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlalchemy.dialects.sqlite import insert as sqlite_insert


class KnowledgeDatabase:
    def __init__(
        self,
        sync_url: str,
        async_url: str,
        base_model: DeclarativeBase,
        *,
        expire_on_commit: bool = False,
        autoflush: bool = False,
    ):
        # this 
        if not sync_url.startswith("sqlite:///") or not async_url.startswith("sqlite+aiosqlite:///"):
            raise NotImplementedError(f"For now, only SQLite databases with aiosqlite for async connections are supported, got sync_url='{sync_url}' and async_url='{async_url}'")

        self._engine = create_engine(sync_url)
        self._async_engine = create_async_engine(async_url)
        self.expire_on_commit = expire_on_commit
        self.autoflush = autoflush
        self._sessionmaker = sessionmaker(self._engine, expire_on_commit=self.expire_on_commit, autoflush=self.autoflush)
        self._async_sessionmaker = async_sessionmaker(self._async_engine, expire_on_commit=self.expire_on_commit, autoflush=self.autoflush)
        base_model.metadata.create_all(self._engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        _session = self._sessionmaker()
        try:
            yield _session
            # context manager gives control back to code
            _session.commit()  # autocommit at the exit
        except Exception as e:
            _session.rollback()
            raise e
        finally:
            _session.close()

    @asynccontextmanager
    async def async_session(self) -> AsyncIterator[AsyncSession]:
        _session = self._async_sessionmaker()
        try:
            yield _session
            # context manager gives control back to code
            await _session.commit()  # autocommit at the exit
        except Exception as e:
            await _session.rollback()
            raise e
        finally:
            await _session.close()

    async def upsert(self, model, unique_columns: list[str], params: dict[str, Any], session: AsyncSession) -> Any:
        """Upserts the entity in the database, using the columns from `unique_columns` (**which should compose a unique key**) to decide if the record already exists or not.
        
        Does not flush changes.

        Args:
            model (_type_): database entity / table
            unique_columns (list[str]): columns used as a unique key that defines if the record being upserted already exists (i.e should just be updated) or not (i.e should be inserted).
            params (dict[str, Any]): params for the upsert
            session (AsyncSession): async db session

        Return:
            The upserted instance. The type is the same type passed as the `model` argument.
        """
        # NOTE: for now we know for sure the db is sqlite due to the if guard in the __init__
        # TODO: maybe clean this up
        insert_stmt = sqlite_insert(model).values(**params)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[getattr(model, col) for col in unique_columns],
            set_=params,
        ).returning(model)
        return (await session.execute(upsert_stmt)).scalar_one()
