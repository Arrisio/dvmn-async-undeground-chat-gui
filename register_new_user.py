import asyncio
import sys
import os
import re
import tkinter as tk
from socket import gaierror
from tkinter import messagebox

import asyncclick as click
from anyio import create_task_group
from loguru import logger

import gui
from chat import chat_connection, ParseServerResponseException, register
from settings import Settings


async def registration(registration_queue, host, send_port):
    while True:
        user_name = await registration_queue.get()
        async with chat_connection(host, send_port) as (
            reader,
            writer,
        ):
            chat_token = await register(user_name, reader, writer)
            write_down_token(chat_token)
            logger.info("received token", extra={"token": chat_token})
            tk.messagebox.showinfo("register successfully", f"your token: {chat_token} \nsaved to .env file")


def write_down_token(token, env_filename=".env"):
    new_token_string = f"CHAT_TOKEN={token}"

    if not os.path.isfile(env_filename):
        with open(env_filename, "w") as fh:
            fh.write(new_token_string)
            return

    token_pattern = re.compile(
        r"CHAT_TOKEN=[ \t]*[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[89ab][a-f0-9]{3}-[a-f0-9]{12}",
        re.IGNORECASE,
    )
    with open(env_filename, "r") as fh:
        envs = fh.read()

        if token_pattern.findall(envs):
            envs = token_pattern.sub(new_token_string, envs)
        else:
            envs += "\n" + new_token_string
    with open(env_filename, "w") as fh:
        fh.write(envs)


async def draw(register_queue):
    root = tk.Tk()
    root.title("Регистрация пользователя")

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True, padx=25, pady=20)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    user_name_label = tk.Label(input_frame, text="Имя нового пользователя")
    user_name_label.pack(anchor=tk.NW)

    input_field = tk.Entry(input_frame)
    input_field.bind("<Return>", lambda _: register_queue.put_nowait(input_field.get()))
    input_field.pack(side="left", fill=tk.X, expand=True)

    send_button = tk.Button(input_frame, height=1)
    send_button["text"] = "Зарегистрироваться"
    send_button["command"] = lambda: register_queue.put_nowait(input_field.get())
    send_button.pack(padx=10)

    await gui.update_tk(root_frame)


@click.command()
@click.option("-h", "--host", default=Settings().HOST, help="chat hostname")
@click.option("--send_port", default=Settings().SEND_PORT)
async def main(host, send_port):
    logger.configure(
        **{
            "handlers": [
                {
                    "sink": sys.stdout,
                    "format": "<level>{level: <8} {time:HH:mm:ss}</level>|<cyan>{name:<12}</cyan>:<cyan>{function:<24}</cyan>:<cyan>{line}</cyan> - <level>{message:>32}</level> |{extra}",
                },
            ],
        }
    )

    register_queue = asyncio.Queue()
    try:
        async with create_task_group() as tg:
            await tg.spawn(draw, register_queue)
            await tg.spawn(registration, register_queue, host, send_port)

    except gui.TkAppClosed:
        logger.warning("gui was closed. exiting ..")

    except (
        ConnectionError,
        ConnectionAbortedError,
        ConnectionRefusedError,
        gaierror,
        asyncio.exceptions.CancelledError,
        TimeoutError,
    ) as e:
        logger.error("can`t connect to chat", extra={"host": host})

    except ParseServerResponseException as e:
        logger.error(e.__repr__(), extra={"host": host})


if __name__ == "__main__":
    asyncio.run(main())
