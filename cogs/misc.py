from datetime import datetime

import discord
from discord.ext import commands
import humanize


class MiscCommands(commands.Cog, name="Misc"):
    """Miscellaneous commands"""
    big_map_url = "https://raw.githubusercontent.com/Aryezz/Map-Art-Helper-Bot/refs/heads/main/map_arts.csv"

    def __init__(self, bot):
        self.bot = bot
        self.bot.help_command.cog = self
        self.biggest_maps = []

    @commands.command()
    async def mafta(self, ctx):
        """Info about MAFTA"""
        message = (
            "[MAFTA](<https://en.wikipedia.org/wiki/North_American_Free_Trade_Agreement>) stands for Map Art Free Trade Agreement\n"
            "Members of the MAFTA give away their maps for free."
        )

        await ctx.send(message)

    @commands.command()
    async def info(self, ctx):
        """Info about the bot"""
        description = (
            "Map Art Helper bot made with :heart: by Aryezz#9352\n"
            "Feel free to suggest ideas for improvements / new commands\n"
            "Source Code: https://github.com/Aryezz/Map-Art-Helper-Bot"
        )
        url = "https://cdn.discordapp.com/avatars/241663921390485506/a_21562dbefcd6abff27bff9e98a1e317f.gif?size=1024"
        embed = discord.Embed(title="Map Art Helper", description=description, colour=discord.Colour.gold())
        embed.set_thumbnail(url=url)

        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def reload(self, ctx):
        """Reloads all cogs"""
        for extension in list(self.bot.extensions.keys()):
            await self.bot.reload_extension(extension)

        await ctx.send("reloaded all cogs")

    @commands.command()
    async def uptime(self, ctx):
        """Shows the bot uptime"""
        delta = self.bot.started - datetime.now()
        delta_f = humanize.precisedelta(delta, minimum_unit="seconds", suppress=["years", "months"], format="%d")
        msg = f"Uptime: {delta_f}"

        await ctx.send(msg)


async def setup(client):
    await client.add_cog(MiscCommands(client))
