import os
import discord
import jinja2

from discord.ext import commands, tasks
from multiprocessing.connection import Connection
from datetime import datetime
from typing import Dict, List, Union

from conversation import Conversation, Message, Exchange
from config import Config


TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CMD_PREFIX = '/'
MESSAGE_FETCH_LIMIT = 50


class Bot(commands.Bot):
    conf: Config
    bot_recv: Connection
    llm_send: Connection
    conversations: Dict[int, Conversation]
    token_len: int
    jenv: jinja2.Environment

    def __init__(self, conf: Config, bot_recv: Connection, llm_send: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conf = conf
        self.bot_recv = bot_recv
        self.llm_send = llm_send
        self.conversations = {}
        self.jenv = jinja2.Environment()

        # Conversations should be lte the max context window minus the max response tokens minus 1000 (for system prompts).
        # The extra buffer ensures we aren't maxing out the context window since the LLM will likely have enough context.
        # TODO: Possible optimization: after each exchange, ask the LLM to reword its response and then store the new result.
        self.token_len = 4096 - conf.completions['n_predict'] - 1000

    async def record(self, message: discord.Message):
        if not message.channel.id in self.conversations:
            conversation = Conversation(
                bot_id=self.user.id,
                messages_len=MESSAGE_FETCH_LIMIT,
                token_len=self.token_len,
                roles=self.conf.roles)
            for m in [m async for m in message.channel.history(limit=MESSAGE_FETCH_LIMIT)]:
                if m.pinned:
                    break
                if not m.content.startswith(CMD_PREFIX) and not m.is_system():
                    conversation.prepend(m)
            self.conversations[message.channel.id] = conversation
            return
        self.conversations[message.channel.id].append(message)

    async def replay(self, message: discord.Message) -> List[Message]:
        if not message.channel.id in self.conversations:
            await self.record(message)
        return self.conversations[message.channel.id].replay()

    async def replay_from(self, channel: Union[discord.TextChannel, discord.Thread], start: datetime, end: datetime) -> List[Message]:
        conversation = Conversation(
            self.user.id, MESSAGE_FETCH_LIMIT, self.token_len, self.roles)
        for m in [m async for m in channel.history(limit=MESSAGE_FETCH_LIMIT, before=end)]:
            if m.created_at < start:
                break
            if not m.content.startswith(CMD_PREFIX) and not m.is_system():
                conversation.prepend(m)
        return conversation.replay()

    def generate(self, ctx: commands.Context, messages: List[Message], completion_opts: Dict = {}):
        prompt = self.jenv.from_string(self.conf.template.body).render(
            system=self.conf.template.system,
            exchanges=[Exchange(messages[i], messages[i+1]) for i in range(0, len(messages)-1, 2)]
        )
        self.recv_complete(ctx)
        self._recv.start()
        self.llm_send.send((prompt, completion_opts,))

    def recv_complete(self, ctx: commands.Context):
        @tasks.loop(seconds=1.0)
        async def recv():
            if not self.bot_recv.poll():
                return
            line = self.bot_recv.recv()
            line = line.strip()
            if line == 'EOF':
                print('<EOF>')
                self._recv.stop()
                self._recv = None
                return
            elif line:
                print(line)
                await ctx.send(line)
        self._recv = recv
