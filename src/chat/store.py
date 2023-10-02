import textract
import os

from urllib.request import urlretrieve
from discord.ext import commands

from bot import Bot
from db.store import Document, Store
from conversation import Message


UPLOAD_TYPES = [
    'pdf', 'docx', 'doc', 'html', 'rtf', 'epub'
    "gif", "png", "jpg", "jpeg",
    "tiff", "mp3", "ogg", "wav",
    "pptx", "xlsx", "xls"
]


class Ingest(commands.Cog):
    store: Store

    def __init__(self, bot: Bot):
        self.bot = bot
        self.store = Store(self.bot.conf)

    @commands.command(brief='Ingest data from a URL')
    async def ingest(self, ctx: commands.Context, url: str, extension: str = ''):
        if not url:
            return await ctx.message.add_reaction('❌')
        if not extension:
            extension = url[url.rindex('.')+1:]
        if not extension in UPLOAD_TYPES:
            return await ctx.message.add_reaction('❌')

        downloaded, _ = urlretrieve(url)
        bs: bytes = textract.process(downloaded,
                                     extension=extension,
                                     output_encoding='utf-8',
                                     layout=False)
        os.remove(downloaded)
        content = bs.decode()
        self.store.add(Document(url, content))
        await ctx.message.delete()


async def setup(bot):
    await bot.add_cog(Ingest(bot))
