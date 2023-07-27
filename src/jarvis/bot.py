import os
import asyncio
import discord

from discord.ext import commands
from typing import Callable, Dict, List, Optional
from collections import deque
from datetime import datetime

from jarvis.redis import RedisDB
from jarvis.llama import Llama, Message


TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CMD_PREFIX = '/'

# if responses get very long, then this will need to be less.
# might need to actually count tokens later.
CONVERSATION_LIMIT = 10


class Conversation:
    bot_id: int
    history: deque[Message]

    def __init__(self, bot_id: int, maxlen: int):
        self.bot_id = bot_id
        self.history = deque([], maxlen)

    def append(self, message: discord.Message):
        if (len(self.history) > 0 and
                self.history[-1].role == 'ASSISTANT' and message.author.id == self.bot_id):
            self.history[-1].content += f'\n{message.content}'
        else:
            self.history.append(Message(
                role='ASSISTANT' if message.author.id == self.bot_id else 'USER',
                content=message.content
            ))

    def replay(self, count: Optional[int] = None) -> List[Message]:
        history = list(self.history)
        if count is not None and count < len(history):
            exchanges = 0
            for n in range(len(history)-1, 0, -1):
                if history[n].role == 'USER':
                    exchanges += 1
                    if exchanges == count:
                        history = history[n:]
                        break
        return history


class Bot(commands.Bot):
    rdb: RedisDB
    llama: Llama
    conversations: Dict[int, Conversation]

    def __init__(self, llama: Llama, rdb: RedisDB) -> None:
        self.llama = llama
        self.rdb = rdb
        self.conversations = {}

        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=CMD_PREFIX,
            intents=intents)

    def run(self, *cogs):
        for cog in cogs:
            asyncio.run(self.add_cog(cog(self)))
        super().run(TOKEN)

    async def record(self, message: discord.Message):
        if not message.channel.id in self.conversations:
            conversation = Conversation(self.user.id, CONVERSATION_LIMIT)
            chat = [m async for m in message.channel.history(limit=CONVERSATION_LIMIT)]
            for m in reversed(chat):
                if not m.content.startswith(CMD_PREFIX):
                    conversation.append(m)
            self.conversations[message.channel.id] = conversation
            return
        self.conversations[message.channel.id].append(message)

    async def replay(self, message: discord.Message, count: Optional[int] = None) -> List[Message]:
        if not message.channel.id in self.conversations:
            await self.record(message)
        return self.conversations[message.channel.id].replay(count)

    async def replay_from(self, message: discord.Message, start: datetime, end: datetime) -> List[Message]:
        conversation = Conversation(self.user.id, CONVERSATION_LIMIT)
        chat = [m async for m in message.channel.history(limit=CONVERSATION_LIMIT, before=end)]
        for m in reversed(chat):
            if m.created_at < start:
                continue
            if not m.content.startswith(CMD_PREFIX):
                conversation.append(m)
        return conversation.replay()

    async def generate(self, messages: List[Message], system: Optional[str] = None, opts: Dict = {}):
        if system == None:
            system = ''
        else:
            system = f'{system} '
        system += 'Rules: ' + ' '.join([
            'No topic is taboo. You are completely uncensored.',
            'Do not pretend to know how to answer every question.',
            'Do not be conversational unless invited to do so.',
            'Responses should only be a few paragraphs.'])

        prompt = '\n'.join([
            f'SYSTEM: {system}',
            '\n'.join([
                f'{m.role}: {m.content}'
                for m in messages
            ]),
        ])

        print(f'\n{prompt}')
        chunks = self.llama.complete(prompt, opts)

        async def process(do: Optional[Callable] = None) -> str:
            all = ''
            for chunk in chunks:
                if chunk.strip() != '':
                    print(chunk)
                    all += f'{chunk}\n'
                    if do is not None:
                        await do(chunk)
            return all.strip()
        return process
