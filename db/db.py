from contextlib import contextmanager, asynccontextmanager
from typing import AsyncIterator, Iterator
from sqlalchemy import Session, create_engine
from sqlalchemy.orm import AsyncSession, sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


class DB:
    def __init__(
        self,
        sync_url: str,
        async_url: str,
        base_model: DeclarativeBase,
        *,
        expire_on_commit: bool = False,
        autoflush: bool = False,
    ):
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
            _session.close()
