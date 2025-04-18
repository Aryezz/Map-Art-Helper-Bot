import hashlib
import re
import io
import random
import math
import logging
import csv
from typing import *
from dataclasses import dataclass
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands
from PIL import Image
import humanize

from cogs import exceptions
from cogs import checks

session = aiohttp.ClientSession()

logger = logging.getLogger("discord.mapart.misc")


@dataclass
class MapMetadata:
    id: int
    rotation: int = 0
    position: Tuple[int, int] = (0, 0)

    async def fetch(self) -> bytes:
        # v parameter is used for caching, using random value to avoid getting outdated images
        url = f"https://mapartwall.rebane2001.com/mapimg/map_{self.id!s}.png?v={random.randint(0, 999_999_999)}"

        async with session.get(url, ssl=False) as resp:
            if not resp.status == 200:
                raise commands.CommandError("Mapartwall responded with response status code " + str(resp.status))

            data = await resp.read()

            return data


@dataclass
class MapArt:
    BLACKLIST = [  # blacklist for maps that violate discord TOS
            "89be42fca8ecce7d821bf36d82d9ffd00157d5b5a943dd379141607412e316b9",
            "ae6d3a992c15ee9b4f004d9e52dde6ed65681a1c0830e35475ac39452b11377b",
            "440dbb039ff6f2d57c0a540c84f0d07e32687c295388be76ec88fca990fc553e",
            "780dcdcf480185c5823b5115c4acbdfb251b45cba5bc09dc533ea9640e75d1e2",
            "9846db0d5cdd13deeea480d36e88bdc263e22dbea0458d90a84e599341a7f5cb",
            "8f3289eec87009bdc6f191c9223b9e753bf6ce86cf5daa9927ae4f2221ae363a",
            "83e247b8454deaeffda10bb621af803853b2598ad633340e7233f20df0160d28",
        ]

    maps: List[MapMetadata]

    async def generate_map(self, ctx, upscale: bool = False) -> discord.File:
        map_art_width = max(meta.position[0] for meta in self.maps) + 1
        map_art_height = max(meta.position[1] for meta in self.maps) + 1
        full_map = Image.new("RGBA", (map_art_width * 128, map_art_height * 128))
        map_cache: Dict[int, bytes] = {}

        for map in self.maps:
            if map.id not in map_cache.keys():
                map_cache[map.id] = await map.fetch()
            map_bytes = map_cache[map.id]

            if hashlib.sha256(map_bytes).hexdigest() in self.BLACKLIST:
                raise exceptions.BlacklistedMapError(map.id, ctx.author)

            img = Image.open(io.BytesIO(map_bytes)).convert("RGBA")

            if img.getextrema()[3][1] < 255:  # Map is completely transparent
                raise exceptions.TransparentMapError(map.id)

            if map.rotation:
                img = img.rotate(map.rotation * -90)

            full_map.paste(img, (map.position[0] * 128, map.position[1] * 128))

        if upscale:  # up-scaling maps for better viewing in the discord client
            full_map = full_map.resize((full_map.width * 4, full_map.height * 4), Image.NEAREST)

        img_bytes = io.BytesIO()
        full_map.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        return discord.File(img_bytes, "map.png")


class SingleMapArt(MapArt):
    @classmethod
    async def convert(cls, ctx, map_id: str):
        if not map_id.isnumeric():
            raise commands.BadArgument("Map ID is not numeric")

        return cls([MapMetadata(id=int(map_id))])


class MultiMapRange(MapArt):
    @classmethod
    async def convert(cls, ctx, argument: str):
        if not (match := re.match(r"^(\d+)\s*-\s*(\d+)\s+(\d+)x(\d+)$", argument)):
            raise commands.BadArgument("Invalid Format")

        first_id, last_id = int(match[1]), int(match[2])
        width, height = int(match[3]), int(match[4])

        if not last_id - first_id + 1 == width * height:
            raise commands.BadArgument("Incorrect number of maps for size")

        if not 0 <= first_id < 32_767 or not 0 <= last_id < 32_767:
            raise commands.BadArgument("Map ID must be between 0 and 32767")

        map_ids = []
        for i, map_id in enumerate(range(first_id, last_id + 1)):
            x, y = i % width, i // width
            map_ids.append(MapMetadata(id=map_id, position=(x, y)))

        return cls(map_ids)


class MultiMapList(MapArt):
    @classmethod
    async def convert(cls, ctx, argument: str):
        if not re.match(r"^\d+(\.[1-3])?(\s*[,;]\s*\d+(\.[1-3])?)*$", argument):
            raise commands.BadArgument("Invalid Format")

        map_ids = []

        for y, line in enumerate(argument.split(";")):
            for x, map_meta in enumerate(line.split(",")):
                split_meta = map_meta.split(".")
                map_id, rot = int(split_meta[0]), int(split_meta[1]) if len(split_meta) == 2 else 0

                if not 0 <= map_id < 32_767:
                    raise commands.BadArgument("Map ID must be between 0 and 32767")

                map_ids.append(MapMetadata(id=map_id, rotation=rot, position=(x, y)))

        return cls(map_ids)


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

    @commands.is_nsfw()
    @commands.command(enabled=False)
    async def stitch(self, ctx, *, map_art: Union[SingleMapArt, MultiMapRange, MultiMapList]):
        """
        Stitches together maps from mapartwall, map_ids has to be one of the following formats:
        * 1234-1239 3x2 (generates 2x2 map with the ids 1234-1238)
        * 1234,1235,1236;1237,1238,1239 (generates the same map, useful when the maps are not in order)
        * 1234,1234.1;1234.3,1234.2 (add periods after an id to rotate the map 1-3 times clockwise)
        """
        async with ctx.channel.typing():
            await ctx.send(file=await map_art.generate_map(ctx))

    @commands.is_nsfw()
    @commands.command(aliases=["id"], enabled=False)
    async def map(self, ctx, map_art: SingleMapArt):
        """Sends a map from mapartwall"""
        async with ctx.channel.typing():
            await ctx.send(file=await map_art.generate_map(ctx, upscale=True))

    @map.error
    @stitch.error
    async def map_error(self, ctx, error):
        error = getattr(error, 'original', error)

        if isinstance(error, exceptions.TransparentMapError):
            await ctx.reply(f"Map {error.map_id!s} is empty.")
        elif isinstance(error, exceptions.BlacklistedMapError):
            logger.error(error)

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

        maps_to_consider: List[BigMapArt] = self.biggest_maps

        # without any filters, the cutoff is 32 individual maps
        # => smaller maps only show up if you explicitly filter
        if len(filters) == 0:
            maps_to_consider = list(filter(lambda m: m.total_maps >= 32, maps_to_consider))

        if any(f in filters for f in filter_flat_options):
            flat_types: List[str] = ["flat", "dual-layered", "flat + terrain"]
            maps_to_consider = list(filter(lambda x: x.type not in flat_types, maps_to_consider))

        if any(f in filters for f in filter_carpet_only_options):
            carpet_only_types: List[str] = ["carpet only", "two-colour", "98.7% carpet"]
            maps_to_consider = list(filter(lambda x: x.palette not in carpet_only_types, maps_to_consider))

        max_page = math.ceil(len(maps_to_consider) / 10)

        if 0 >= page or page > max_page:
            await ctx.reply(f"Page {page} is invalid.")
            return

        maps = maps_to_consider[(page - 1) * 10:page * 10]
        ranks = {1: "🥇", 2: "🥈", 3: "🥉"}

        message = "# Biggest map-art ever built on 2b2t:\n"

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
    async def info(self, ctx):
        """Info about the bot"""
        description = (
            "Map Art Helper bot made with :heart: by Aryezz#9352\n"
            "Feel free to suggest ideas for improvements / new commands\n"
            "Source Code: https://gitlab.com/Aryezz/map-art-helper-bot"
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
