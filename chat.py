import asyncio
import json
from asyncio import Queue, StreamWriter, StreamReader
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Tuple

import aiofiles
from anyio import fail_after, create_task_group
from loguru import logger
from tenacity import retry, wait_fixed, retry_if_exception_type

from exceptions import ParseServerResponseException, WatchdogException, AuthException, CONNECTION_EXCEPTIONS
from gui import SendingConnectionStateChanged, ReadConnectionStateChanged, NicknameReceived
from settings import Settings


@dataclass
class ChatQueues:
    messages_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    save_messages_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    sending_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    status_updates_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    watchdog_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


@asynccontextmanager
async def chat_connection(host: str, port: int) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    logger.debug("trying to connect to server", host=host, port=port)

    try:
        async with fail_after(Settings().CONNECTION_TIMEOUT):
            reader, writer = await asyncio.open_connection(host, port)
    except TimeoutError:
        raise ConnectionError("connection timeout")
    logger.debug("connect to server successfully", host=host, port=port)

    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def authorize(status_updates_queue: Queue, chat_token: str, reader: StreamReader, writer: StreamWriter):
    init_response = (await reader.readline()).decode()
    logger.debug("get init response from server", init_response=init_response)

    writer.write(f"{chat_token}\n".encode())
    await writer.drain()

    auth_response = (await reader.readline()).decode()

    try:
        auth_result = json.loads(auth_response)

    except json.JSONDecodeError:
        raise ParseServerResponseException("error while auth")

    logger.debug("receives auth response", extra=auth_result)
    if not auth_result:
        raise AuthException

    status_updates_queue.put_nowait(NicknameReceived(auth_result["nickname"]))
    logger.info("auth successfully")


async def register(user_name: str, settings: Settings):
    async with chat_connection(settings.HOST, settings.SEND_PORT) as (reader, writer):
        init_response = (await reader.readline()).decode()
        logger.debug(
            "get init response from server",
            extra={"init_response": init_response},
        )

        logger.debug("start registering user", user_name=user_name)
        writer.write(b"\n")
        await writer.drain()

        logger.debug("awaiting login", server_response=await reader.readline())

        writer.write(f"{user_name}\n".encode())
        await writer.drain()

        register_response = await reader.readline()
        logger.debug("register_response received", register_response=register_response.decode())

        try:
            return json.loads(register_response)["account_hash"]
        except json.JSONDecodeError:
            raise ParseServerResponseException("error while registration")


async def sending_msgs_from_queue(sending_queue: Queue, watchdog_queue: Queue, writer: StreamWriter):
    while True:
        message = await sending_queue.get()
        for line in message.splitlines():
            writer.write(f"{line}\n\n".encode())
        await writer.drain()
        logger.debug("message sent successfully", message=message)
        watchdog_queue.put_nowait("Connection is alive. Message sent")


async def ping_pong(watchdog_queue: Queue, reader: StreamReader, writer: StreamWriter):
    while True:
        writer.write("\n".encode())
        await writer.drain()
        await reader.readline()
        watchdog_queue.put_nowait("Ping message was successful")
        await asyncio.sleep(Settings().PING_PONG_INTERVAL)


@retry(
    wait=wait_fixed(Settings().RECONNECT_TIMEOUT),
    retry=retry_if_exception_type(CONNECTION_EXCEPTIONS),
)
async def send_msgs(chat_queues: ChatQueues, settings: Settings):
    chat_queues.status_updates_queue.put_nowait(SendingConnectionStateChanged.INITIATED)
    try:
        if not settings.CHAT_TOKEN:
            settings.CHAT_TOKEN = await register(user_name=settings.USER_NAME, settings=settings)

        async with chat_connection(settings.HOST, settings.SEND_PORT) as (reader, writer):
            await authorize(chat_queues.status_updates_queue, settings.CHAT_TOKEN, reader, writer)

            chat_queues.status_updates_queue.put_nowait(SendingConnectionStateChanged.ESTABLISHED)

            async with create_task_group() as tg:
                tg.start_soon(sending_msgs_from_queue, chat_queues.sending_queue, chat_queues.watchdog_queue, writer)
                tg.start_soon(ping_pong, chat_queues.watchdog_queue, reader, writer)
                tg.start_soon(watch_for_connection, chat_queues)
    except CONNECTION_EXCEPTIONS as err:
        # логируем здесь, т.к. адаптацию tenacity под Loguru еще не зарелизили
        # https://tenacity.readthedocs.io/en/latest/changelog.html
        logger.error("connection error", error=err, host=settings.HOST, port=settings.SEND_PORT)
        raise
    finally:
        chat_queues.status_updates_queue.put_nowait(SendingConnectionStateChanged.CLOSED)


async def watch_for_connection(chat_queues: ChatQueues):
    with logger.contextualize(logger_name="watchdog_logger"):
        while True:
            try:
                async with fail_after(Settings().WATCHDOG_TIMEOUT):
                    msg = await chat_queues.watchdog_queue.get()
                    logger.info(msg)
            except TimeoutError:
                raise WatchdogException("not see ping or human messages")


@retry(
    wait=wait_fixed(Settings().RECONNECT_TIMEOUT),
    retry=retry_if_exception_type(CONNECTION_EXCEPTIONS),
)
async def read_msgs(chat_queues: ChatQueues, settings: Settings):
    try:
        async with chat_connection(settings.HOST, settings.READ_PORT) as (reader, writer):
            while True:
                chat_queues.status_updates_queue.put_nowait(ReadConnectionStateChanged.INITIATED)
                async with fail_after(settings.READ_TIMEOUT):
                    chat_queues.status_updates_queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)
                    if income_message_text := (await reader.readline()).decode(encoding="utf8"):
                        chat_queues.messages_queue.put_nowait(income_message_text)
                        chat_queues.save_messages_queue.put_nowait(income_message_text)
                        chat_queues.watchdog_queue.put_nowait("Connection is alive. New message in chat")
    except CONNECTION_EXCEPTIONS as err:
        logger.error(f"connection error", error=err, host=settings.HOST, port=settings.READ_PORT)
        raise
    finally:
        chat_queues.status_updates_queue.put_nowait(ReadConnectionStateChanged.CLOSED)


async def save_messages(chat_queues: ChatQueues, history_path):
    while True:
        msg = await chat_queues.save_messages_queue.get()
        async with aiofiles.open(history_path, "a") as fh:
            await fh.write(msg)


async def load_chat_history(messages_queue, history_path):
    async with aiofiles.open(history_path, "r") as fh:
        async for line in fh:
            messages_queue.put_nowait(line)
