from ollama import (
    chat as ollama_chat,
    ChatResponse as OllamaChatResponse,
    Message as OllamaMessage,
)
from langchain.prompts import PromptTemplate
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import NoResultFound

from db.chat import CHAT_DB, Chat, Message
from db.db import DB
from prompts import SYSTEM_PROMPT, USER_PROMPT

def get_chat_history(chat: Chat) -> list[OllamaMessage]:
    chat_history = []
    if (not chat.messages) and chat.system_prompt:   # is first message
        chat_history.append(OllamaMessage(role="system", content=chat.system_prompt))
    for msg in chat.messages:
        chat_history.append(OllamaMessage(role=msg.role, content=msg.content))
    return chat_history


async def send_message(
    db: DB,
    chat_id: int | None,
    message: str,
    model_name: str,
    think: bool = False,
) -> Message:
    chat_history = []
    async with db.async_session() as session:
        if chat_id is not None:
            try:
                chat = await session.get_one(Chat, chat_id, options=[selectinload(Chat.messages)])
            except NoResultFound:
                raise ValueError(f"Invalid chat ID: chat ID={chat_id} does not exist")
        else:
            chat = Chat(system_prompt=SYSTEM_PROMPT.template)  # FIXME NOTE: assumes no substitution on system prompt
        chat_history = get_chat_history(chat)
        user_prompt_with_query = USER_PROMPT.format(content=message)
        chat_history.append(OllamaMessage(role="user", content=user_prompt_with_query))
        response = ollama_chat(model_name, messages=chat_history, think=think).message
        chat.messages.extend([
            Message(role="user", content=user_prompt_with_query),
            Message(role=response.role, content=response.content),
        ])
        await session.commit()
    return chat.messages[-1]


## some testing code
if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    chat_id = None
    while True:
        print(">>> ", end="")
        msg = input().strip()
        if (msg == "/exit"):
            print("Exiting now...")
            exit(0)
        response = loop.run_until_complete(
            send_message(
                db=CHAT_DB,
                chat_id=chat_id,
                message=msg,
                model_name="gemma3:4b",
                think=False,
            )
        )
        print(f"[{response.role.upper()}]: '''\n{response.content}\n'''")
        chat_id = response.chat_id
