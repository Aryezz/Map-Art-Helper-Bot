import math
import logging
import csv
from typing import *
from dataclasses import dataclass
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands
import humanize

from cogs import checks

session = aiohttp.ClientSession()

logger = logging.getLogger("discord.mapart.misc")


@dataclass
class BigMapArt:
    size: Tuple[int, int]
    type: str
    palette: str
    name: str
    artists: List[str]
    message_id: int

    @property
    def total_maps(self):
        return self.size[0] * self.size[1]

    @property
    def link(self):
        return "https://discord.com/channels/349201680023289867/349277718954901514/" + str(self.message_id)

    @property
    def artists_str(self):
        if len(self.artists) == 1:
            return self.artists[0]

        return ", ".join(self.artists[:-1]) + " and " + self.artists[-1]

    @property
    def line(self):
        size_info = f"{self.size[0]} x {self.size[1]} ({self.total_maps} maps)"
        extra_info = f"[{self.type}, {self.palette}] - [**{self.name}**]({self.link}) by **{self.artists_str}**"

        return size_info + " - " + extra_info


class MiscCommands(commands.Cog, name="Misc"):
    """Miscellaneous commands"""
    big_map_url = "https://gitlab.com/Aryezz/map-art-helper-bot/-/raw/main/map_arts.csv"

    def __init__(self, bot):
        self.bot = bot
        self.bot.help_command.cog = self
        self.biggest_maps = []

    async def cog_load(self):
        async with session.get(self.big_map_url, ssl=False) as resp:
            if not resp.status == 200:
                raise commands.CommandError("Could not load map data, HTTP status: " + str(resp.status))

            data = await resp.text()

            reader = csv.reader(
                filter(lambda line: not line.strip().startswith("#") and not line.strip() == "", data.split("\n")),
                delimiter=';', quotechar='"')

            for entry in reader:
                width = int(entry[0].strip())
                height = int(entry[1].strip())
                map_type = entry[2].strip()
                palette = entry[3].strip()
                name = entry[4].strip()
                artists = [a.strip() for a in entry[5].split(",")]
                message_id = int(entry[6].strip())
                self.biggest_maps.append(BigMapArt((width, height), map_type, palette, name, artists, message_id))

        # we sort by total maps (descending) and message id (-> message age - ascending)
        # because the ordering is opposite for the two, we invert the message id, so when reversed we get the ascending
        # order that we want. There is probably a more pythonic way to do this, but whatever.
        self.biggest_maps = sorted(self.biggest_maps, key=lambda x: (x.total_maps, x.message_id * -1), reverse=True)

    @checks.is_in_bot_stuff()
    @commands.command(aliases=["largest"])
    async def biggest(self, ctx, *args):
        """The biggest map art on 2b2t

        Usage: !!biggest [args]

        Parameters
        ----------
        args : list, optional
            Page and filters to apply to the list of maps.
            To filter out flat maps, use `-f`,
            to filter out carpet-only maps, use `-c` or `-co`
        """

        filter_flat_options: Set[str] = {"-f", "-flat"}
        filter_carpet_only_options: Set[str] = {"-c", "-co", "-carpet", "-carpetonly", "-carpet-only"}
        legal_arguments: Set[str] = filter_flat_options | filter_carpet_only_options

        # parse page num
        page = 1
        page_arg = [arg for arg in args if arg.isnumeric()]
        if len(page_arg) == 1:
            page = int(page_arg[0])
        elif len(page_arg) > 1:
            raise commands.BadArgument("Can only have one page number")

        filters = {arg for arg in args if arg in legal_arguments}

        name_filter = []
        for i in range(len(args) - 1):  # only loop to second last argument, because name still comes after
            if args[i] == "-n":
                name_filter.append(args[i + 1])

        title_note = []
        maps_to_consider: List[BigMapArt] = self.biggest_maps

        # without any filters, the cutoff is 32 individual maps
        # => smaller maps only show up if you explicitly filter
        if len(filters) == 0 or len(name_filter) > 0:
            maps_to_consider = list(filter(lambda m: m.total_maps >= 32, maps_to_consider))

        if any(f in filters for f in filter_flat_options):
            flat_types: List[str] = ["flat", "dual-layered", "flat + terrain"]
            maps_to_consider = list(filter(lambda m: m.type not in flat_types, maps_to_consider))
            title_note.append("No flat maps")

        if any(f in filters for f in filter_carpet_only_options):
            carpet_only_types: List[str] = ["carpet only", "two-colour", "98.7% carpet"]
            maps_to_consider = list(filter(lambda m: m.palette not in carpet_only_types, maps_to_consider))
            title_note.append("No carpet-only maps")

        for artist in name_filter:
            maps_to_consider = list(filter(lambda m: artist.lower() in map(lambda a: a.lower(), m.artists), maps_to_consider))

        if name_filter:
            name_list = ", ".join(name_filter[:-1]) + " and " + name_filter[-1] if len(name_filter) > 1 else name_filter[0]
            title_note.append(f"by {name_list}")

        max_page = math.ceil(len(maps_to_consider) / 10)

        if 0 >= page or page > max_page:
            await ctx.reply(f"No results")
            return

        maps = maps_to_consider[(page - 1) * 10:page * 10]
        ranks = {1: "🥇", 2: "🥈", 3: "🥉"}

        message = f"# Biggest map-art ever built on 2b2t{(" (" + ", ".join(title_note) + ")") if title_note else ""}:\n"

        for (i, bigmap) in enumerate(maps):
            rank = i + 1 + (page - 1) * 10
            message += f"**{ranks.get(rank, f'{rank}:')}** {bigmap.line}\n"

        message += f"\n_Page {page}/{max_page}"
        filters_joined = (' ' + ' '.join(filters)) if filters else ""
        if page < max_page:
            message += f" - use `!!biggest {page + 1}{filters_joined}` to see next page"
        elif page > 1:  # only show previous page hint if not on first page
            message += f" - use `!!biggest {page - 1}{filters_joined}` to see previous page"
        message += "_"  # end italics

        if len(message) <= 2000:
            await ctx.send(message)
        else:
            lines = message.split("\n")
            await ctx.send("\n".join(lines[:6]))
            await ctx.send("\n".join(lines[6:]))

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
