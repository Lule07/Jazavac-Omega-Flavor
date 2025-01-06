import discord
from discord.ext import commands


class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot

    @commands.slash_command(name="ping")
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond(
            f"Pong! Latency: {round(self.bot.latency * 1000)}ms", ephemeral=True
        )


def setup(bot):
    bot.add_cog(Utils(bot))
