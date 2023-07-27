import discord

from discord.ext import commands
from datetime import datetime
from typing import List

from jarvis.llama import Message
from jarvis.bot import Bot, CMD_PREFIX
from jarvis.redis import ConversationRef


TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S.%f%z'


class Messaging(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Jarvis initialized')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only record non-command messages
        if message.content.startswith(CMD_PREFIX):
            return
        await self.bot.record(message)

        # Prevent generating responses to itself
        if message.author.id == self.bot.user.id:
            return

        await message.add_reaction('🧠')
        # Limit the context window when coding, and send all at once.
        if message.channel.name == 'code':
            messages = await self.bot.replay(message, 2) + [Message(role='ASSISTANT')]
            process = await self.bot.generate(messages)
            await message.channel.send(await process())
        else:
            messages = await self.bot.replay(message) + [Message(role='ASSISTANT')]
            process = await self.bot.generate(messages, message.channel.topic)
            await process(message.channel.send)
        await message.remove_reaction('🧠', self.bot.user)

    @commands.command()
    async def code(self, ctx: commands.Context):
        await ctx.message.add_reaction('🧠')
        content = (ctx.message.content
                      .removeprefix(''.join([CMD_PREFIX, 'code']))
                      .strip())
        ctx.message.content = content
        await self.bot.record(ctx.message)
        messages = await self.bot.replay(ctx.message, 3) + [Message(role='ASSISTANT')]
        process = await self.bot.generate(messages)
        await ctx.send(await process())
        await ctx.message.remove_reaction('🧠', self.bot.user)

    @commands.command()
    async def reset(self, ctx: commands.Context):
        if ctx.channel.id in self.bot.conversations:
            del self.bot.conversations[ctx.channel.id]
        await self.bot.record(ctx.message)
        await ctx.message.delete()


class Bookmarks(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command()
    async def bookmark(self, ctx: commands.Context):
        if ctx.message.reference is None:
            return await ctx.message.add_reaction('❌')
        await ctx.message.add_reaction('🧠')
        ref = await ctx.fetch_message(ctx.message.reference.message_id)
        start = ref.created_at
        end = ctx.message.created_at
        messages = await self.bot.replay_from(ctx.message, start, end) + [
            Message(role='SYSTEM', content='Make a single sentence synopsis for this conversation.'),
            Message(role='ASSISTANT', content='A conversation about ')
        ]
        system = '\n'.join([
            'Your job is to make a synopsis for this conversation.',
            'Your synopsis will be read aloud by a screen reader, so format accordingly.',
            'Keep your sentences brief and easy to follow.'])
        process = await self.bot.generate(messages, system)
        summary = await process()
        summary = f'A conversation about {summary}'
        embed = discord.Embed(description=summary)
        m = await ctx.send(embed=embed)
        self.bot.rdb.set(ConversationRef(
            guild=str(m.guild.id),
            channel=str(m.channel.id),
            message=str(m.id),
            start=str(start),
            end=str(end),
            summary=summary))
        await ctx.message.remove_reaction('🧠', self.bot.user)
        await m.add_reaction('🔖')

    @commands.command()
    async def bookmarks(self, ctx: commands.Context):
        for doc in self.bot.rdb.list(ctx.guild.id, ctx.channel.id):
            embed = discord.Embed(description=doc.summary)
            ref = discord.MessageReference(
                guild_id=int(doc.guild),
                channel_id=int(doc.channel),
                message_id=int(doc.message))
            try:
                await ctx.send(embed=embed, reference=ref)
            except:
                self.bot.rdb.delete(ref.guild_id, ref.channel_id, ref.message_id)

    @commands.command()
    async def delete(self, ctx: commands.Context):
        if ctx.message.reference is None:
            message_id = (ctx.message.content
                          .removeprefix(''.join([CMD_PREFIX, 'delete']))
                          .strip())
            ctx.message.reference = discord.MessageReference(
                guild_id=ctx.guild.id,
                channel_id=ctx.channel.id,
                message_id=int(message_id))
        ref = ctx.message.reference
        if not self.bot.rdb.delete(ref.guild_id, ref.channel_id, ref.message_id):
            return await ctx.message.add_reaction('❌')
        await ctx.message.delete()

    @commands.command()
    async def replay(self, ctx: commands.Context):
        if ctx.message.reference is None:
            return await ctx.message.add_reaction('❌')
        chain = ctx.message
        while chain.reference is not None:
            chain = await ctx.fetch_message(chain.reference.message_id)
        doc = self.bot.rdb.get(ctx.guild.id, ctx.channel.id, chain.id)
        messages = await self.bot.replay_from(
            ctx.message,
            datetime.strptime(doc.start, TIMESTAMP_FMT),
            datetime.strptime(doc.end, TIMESTAMP_FMT))
        chat = '/replayed\n' + '\n'.join([
            f'{m.role}: {m.content}'
            for m in messages
        ])
        await ctx.send(chat)

    @commands.command()
    async def ref(self, ctx: commands.Context):
        await ctx.message.add_reaction('🧠')
        content = (ctx.message.content
                   .removeprefix(''.join([CMD_PREFIX, 'ref']))
                   .strip())
        doc = None
        chain = ctx.message
        if chain.reference is not None:
            while chain.reference is not None:
                chain = await ctx.fetch_message(chain.reference.message_id)
            doc = self.bot.rdb.get(ctx.guild.id, ctx.channel.id, chain.id)
        if doc is None:
            for d in self.bot.rdb.search(content, 1):
                doc = d
        messages: List[Message] = []
        if doc is not None:
            messages = await self.bot.replay_from(
                ctx.message,
                datetime.strptime(doc.start, TIMESTAMP_FMT),
                datetime.strptime(doc.end, TIMESTAMP_FMT))
            embed = discord.Embed(description=f'"{messages[0].content}... {content}"')
            ref = discord.MessageReference(
                guild_id=int(doc.guild),
                channel_id=int(doc.channel),
                message_id=int(doc.message))
            await ctx.send(embed=embed, reference=ref)
        messages += [
            Message(role='USER', content=content),
            Message(role='ASSISTANT')
        ]
        process = await self.bot.generate(messages)
        await process(ctx.send)
        await ctx.message.remove_reaction('🧠', self.bot.user)
