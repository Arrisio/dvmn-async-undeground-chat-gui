import asyncio
import sys
from socket import gaierror
from tkinter import messagebox

import asyncclick as click
from anyio import create_task_group, ExceptionGroup
from loguru import logger

import gui
from chat import (
    send_msgs,
    AuthException,
    ParseServerResponseException,
    ChatQueues,
    watch_for_connection,
    save_messages,
    read_msgs,
    load_chat_history,
)
from settings import Settings


async def handle_connection(chat_queues, settings):

    while True:

        try:
            async with create_task_group() as tg:
                await tg.spawn(send_msgs, chat_queues, settings)
                await tg.spawn(read_msgs, chat_queues, settings)
                await tg.spawn(watch_for_connection, chat_queues)
        except (
            ConnectionError,
            ConnectionAbortedError,
            ConnectionRefusedError,
            gaierror,
            asyncio.exceptions.CancelledError,
            TimeoutError,
            ExceptionGroup,
        ) as err:
            if isinstance(err, ExceptionGroup) and not any(
                [isinstance(e, ConnectionAbortedError) for e in err.exceptions]
            ):
                raise

            chat_queues.status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            chat_queues.status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            logger.error(
                "connection error, trying to reconnect", extra={"host": settings.HOST, "error_message": str(err)}
            )
            await asyncio.sleep(settings.RECONNET_TTIMEOUT)


@click.command()
@click.option("-h", "--host", default=Settings().HOST, help="chat hostname")
@click.option("--read_port", default=Settings().READ_PORT)
@click.option("--send_port", default=Settings().SEND_PORT)
@click.option(
    "--history ",
    "-H",
    "history_path",
    default=Settings().HISTORY_PATH,
    help="path to write chat history",
    type=click.Path(exists=False, dir_okay=False, readable=True),
)
@click.option("-t", "--chat_token", default=Settings().CHAT_TOKEN, help="chat authenticate token")
@click.option(
    "-u",
    "--user_name",
    default=Settings().USER_NAME,
    help="if auth token is not provided, new user will be registered with this  username",
)
@click.option("-l", "--log_level", default=Settings().LOG_LEVEL)
async def main(host, read_port, send_port, history_path, chat_token, user_name, log_level):
    settings = Settings(
        CHAT_TOKEN=chat_token,
        HOST=host,
        READ_PORT=read_port,
        SEND_PORT=send_port,
        HISTORY_PATH=history_path,
        USER_NAME=user_name,
    )

    logger.configure(
        **{
            "handlers": [
                {
                    "sink": sys.stdout,
                    "format": "<level>{level: <8} {time:HH:mm:ss}</level>|<cyan>{name:<12}</cyan>:<cyan>{function:<24}</cyan>:<cyan>{line}</cyan> - <level>{message:>32}</level> |{extra}",
                    "filter": lambda rec: "logger_name" not in rec["extra"],
                    "level": log_level,
                },
                {
                    "sink": sys.stdout,
                    "format": "[{time:X}] {message}",
                    "filter": lambda rec: rec["extra"].get("logger_name") == "watchdog_logger",
                },
            ],
        }
    )

    chat_queues = ChatQueues()
    await load_chat_history(chat_queues.messages_queue, history_path)

    try:
        async with create_task_group() as tg:
            await tg.spawn(handle_connection, chat_queues, settings)
            await tg.spawn(save_messages, chat_queues, history_path)
            await tg.spawn(gui.draw, chat_queues)

    except gui.TkAppClosed:
        logger.warning("gui was closed. exiting ..")

    except AuthException:
        messagebox.showerror("Неверный токен", "Проверьте токен, сервер его не узнал")
        logger.error("chat token is not valid. exiting ...")

    except ParseServerResponseException as e:
        logger.error(e.__repr__(), extra={"host": host})


if __name__ == "__main__":
    main()
