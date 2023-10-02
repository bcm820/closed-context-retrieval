import discord

from discord.ext import commands

from bot import Bot, CMD_PREFIX
from conversation import Message
from db.store import Store


class Messages(commands.Cog):
    store: Store

    def __init__(self, bot: Bot):
        self.bot = bot
        self.store = Store(self.bot.conf)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content.startswith(CMD_PREFIX) or message.is_system():
            return
        
        await self.bot.record(message)

        # Prevent generating responses to itself
        if message.author.id == self.bot.user.id:
            return
        
        ctx = await self.bot.get_context(message)
        messages = await self.bot.replay(message)

        docs = self.store.search(message.content)
        if len(docs):
            prompt = self.bot.jenv.from_string(self.bot.conf.template.prompt).render(
                documents=docs,
                request=message.content
            )
            messages = messages[:-1] + [Message(role=self.bot.conf.roles.user, content=prompt)]

        self.bot.generate(ctx, messages + [Message(role=self.bot.conf.roles.assistant)])


async def setup(bot):
    await bot.add_cog(Messages(bot))
