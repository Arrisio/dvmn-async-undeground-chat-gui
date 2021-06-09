import logging
from tkinter import messagebox

import asyncclick as click
from anyio import create_task_group

import gui
from chat import send_msgs, ChatQueues, save_messages, read_msgs, load_chat_history
from exceptions import ParseServerResponseException, AuthException
from settings import ChatRuntimeSettings, configure_watchdog_logger

logger = logging.getLogger(__name__)


@click.command()
@click.option("-h", "--host", default=lambda: ChatRuntimeSettings().HOST, help="chat hostname")
@click.option("--read_port", default=lambda: ChatRuntimeSettings().READ_PORT)
@click.option("--send_port", default=lambda: ChatRuntimeSettings().SEND_PORT)
@click.option(
    "--history ",
    "-H",
    "history_path",
    default=lambda: ChatRuntimeSettings().HISTORY_PATH,
    help="path to write chat history",
    type=click.Path(exists=False, dir_okay=False, readable=True),
)
@click.option("-t", "--chat_token", default=lambda: ChatRuntimeSettings().CHAT_TOKEN, help="chat authenticate token")
@click.option(
    "-u",
    "--user_name",
    default=lambda: ChatRuntimeSettings().USER_NAME,
    help="if auth token is not provided, new user will be registered with this  username",
)
@click.option("-l", "--log_level", default=lambda: ChatRuntimeSettings().LOG_LEVEL)
async def main(host, read_port, send_port, history_path, chat_token, user_name, log_level):

    settings = ChatRuntimeSettings(
        CHAT_TOKEN=chat_token,
        HOST=host,
        READ_PORT=read_port,
        SEND_PORT=send_port,
        HISTORY_PATH=history_path,
        USER_NAME=user_name,
        LOG_LEVEL=log_level,
    )

    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s",
    )
    configure_watchdog_logger()

    chat_queues = ChatQueues()
    await load_chat_history(chat_queues.messages_queue, history_path)

    try:
        async with create_task_group() as tg:
            tg.start_soon(send_msgs, chat_queues, settings)
            tg.start_soon(read_msgs, chat_queues, settings)
            tg.start_soon(save_messages, chat_queues, history_path)
            tg.start_soon(gui.draw, chat_queues)

    except (gui.TkAppClosed, KeyboardInterrupt):
        logger.info("gui was closed. exiting ..")

    except AuthException:
        messagebox.showerror("Неверный токен", "Проверьте токен, сервер его не узнал")
        logger.error("chat token is not valid. exiting ...")

    except ParseServerResponseException as err:
        logger.error(f"{err} | host= {host}")


if __name__ == "__main__":
    main()
