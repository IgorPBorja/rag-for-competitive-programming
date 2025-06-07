from datetime import datetime, timezone
from typing import Annotated
from sqlalchemy import (
    TEXT, TIMESTAMP, VARCHAR, ForeignKey, event, Connection, func
)
from sqlalchemy.orm import (
    Mapped, Mapper, mapped_column, declarative_base, relationship
)

from db.db import DB

SYNC_URL = "sqlite:///dataset.db"
ASYNC_URL = "sqlite+aiosqlite:///dataset.db"
BaseModel = declarative_base()

datetime_default_now = Annotated[Mapped[datetime], mapped_column(TIMESTAMP, default=datetime.now(), server_default=func.now())]

class Chat(BaseModel):
    __tablename__ = "chat"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(TEXT)  # chat title, for future use
    system_prompt: Mapped[str | None] = mapped_column(TEXT)
    created_at: Mapped[datetime_default_now]
    updated_at: Mapped[datetime_default_now]
    deleted_at: Mapped[datetime | None]

    messages: Mapped[list["Message"]] = relationship(back_populates="chat")


class Message(BaseModel):
    __tablename__ = "message"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id"))
    content: Mapped[str] = mapped_column(TEXT)
    role: Mapped[str] = mapped_column(VARCHAR(255))
    created_at: Mapped[datetime_default_now]
    updated_at: Mapped[datetime_default_now]
    deleted_at: Mapped[datetime | None]

    chat: Mapped["Chat"] = relationship(back_populates="messages")


@event.listens_for(Chat, "before_update")
@event.listens_for(Message, "before_update")
def refresh_updated_at(mapper: Mapper, conn: Connection, instance):
    # if any columns changed (not counting multi-valued columns/relationships)
    if(
        hasattr(instance, "updated_at")
    ):
        instance.updated_at = datetime.now(tz=timezone.utc)   # all timestamps are in UTC

CHAT_DB = DB(SYNC_URL, ASYNC_URL, BaseModel)
