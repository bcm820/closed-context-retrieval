import asyncio
import uvloop
import discord
import yaml
import logging
import torch.multiprocessing as mp

from multiprocessing.connection import Connection

from config import Config
from llama import Llama
from bot import Bot, CMD_PREFIX, TOKEN


def run_bot(bot_recv: Connection, llm_send: Connection):
    async def run():
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.reactions = True
        intents.dm_reactions = True
        intents.members = True
        bot = Bot(conf=conf,
                  bot_recv=bot_recv,
                  llm_send=llm_send,
                  command_prefix=CMD_PREFIX,
                  case_insensitive=True,
                  intents=intents)
        await bot.load_extension('chat.messages')
        await bot.load_extension('chat.store')
        await bot.load_extension('chat.util')
        await bot.start(TOKEN)
    asyncio.run(run())


if __name__ == "__main__":
    with open('config.yaml') as stream:
        data = yaml.safe_load(stream)
    conf = Config(**data)

    mp.set_start_method('fork')
    mp.log_to_stderr(logging.DEBUG)
    discord.utils.setup_logging()
    uvloop.install()

    llm_recv, llm_send = mp.Pipe(duplex=False)
    bot_recv, bot_send = mp.Pipe(duplex=False)
    proc = mp.Process(target=run_bot, args=(bot_recv, llm_send))
    proc.start()
    Llama(conf, llm_recv, bot_send)
