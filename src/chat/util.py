import discord
import pandas as pd
import math

from discord.ext import commands
from pynvml.smi import nvidia_smi

from bot import Bot


class Util(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Jarvis initialized')

    @commands.command(brief='Reset conversation history')
    async def reset(self, ctx: commands.Context):
        if self.bot.conversations.pop(ctx.channel.id, None):
            await self.bot.record(ctx.message)
        await ctx.message.delete()

    @commands.command(brief='Request further elaboration from the model')
    async def next(self, ctx: commands.Context):
        await ctx.message.delete()
        self.bot.generate(ctx, await self.bot.replay(ctx.message))

    @commands.command(brief='Check GPU status')
    async def status(self, ctx: commands.Context):
        nvsmi = nvidia_smi.getInstance()
        status = nvsmi.DeviceQuery(','.join([
            'pstate', 'temperature.gpu',
            'utilization.gpu', 'utilization.memory',
            'memory.total', 'memory.used',
        ]))
        df = pd.DataFrame.from_records(list(map(lambda gpu: {
            'pstate': gpu["performance_state"],
            'gpu': f'{gpu["utilization"]["gpu_util"]}%',
            'memory': f'{gpu["utilization"]["memory_util"]}%',
            'temp': f'{math.ceil(gpu["temperature"]["gpu_temp"] * 1.8) + 32}°F'
        }, status['gpu'])))
        table = df.to_markdown(headers='keys', tablefmt='psql', index=False)
        await ctx.send('/status', embed=discord.Embed(description=f'```markdown\n{table}\n```'))
        await ctx.message.delete()


async def setup(bot):
    await bot.add_cog(Util(bot))
