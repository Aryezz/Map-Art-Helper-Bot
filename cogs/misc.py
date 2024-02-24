import hashlib
import re
import io
import random
import math
import logging
from typing import *
from dataclasses import dataclass
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands
from PIL import Image
import humanize

from cogs import exceptions

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
        size_info = f"{self.size[0]} x {self.size[1]}, ({self.total_maps} maps)"
        extra_info = f"[{self.type}, {self.palette}] - [**{self.name}**]({self.link}) by **{self.artists_str}**"

        return size_info + " - " + extra_info


class MiscCommands(commands.Cog, name="Misc"):
    """Miscellaneous commands"""

    biggest_maps = [
        BigMapArt((27, 16), "dual-layered", "two-colour", "no comment", ["popstonia"], 910748616283545640),
        BigMapArt((21, 12), "staircased", "full colour", "Angel's Mirror", ["KevinKC2014"], 953371453447884851),
        BigMapArt((11, 11), "flat", "98.7% carpet", "Mapopoly", ["T Gang"], 957248581339844668),
        BigMapArt((8, 8), "dual-layered", "carpet only", "ponystonia", ["popstonia"], 954851826770018364),
        BigMapArt((8, 8), "flat + terrain", "full colour", "Sky Masons", ["The Spawn Masons"], 916099357823103038),
        BigMapArt((9, 6), "flat", "two-colour", "Abaddons Last Art", ["Phi", "Albatros", "Tae"], 650500181573500928),
        BigMapArt((7, 7), "flat", "carpet only", "Fox Portrait", ["FoxMe"], 1161077180445499464),
        BigMapArt((8, 5), "flat", "full colour", "Deathly Hallows", ["Aryezz", "IronException", "THCFree", "Sanku"],
                  859364782891991040),
        BigMapArt((8, 4), "flat", "full colour", "Gotta Catch Em' All", ["Harri"], 616841031605944360),
        BigMapArt((11, 16), "flat", "carpet only", "The Diary", ["CirocDrip"], 1203487381878079548),
        BigMapArt((15, 10), "flat", "carpet only", "sick fearless bastard", ["nyxis", "GAN G SEA LANTERN"],
                  1203487345177788446),
        BigMapArt((9, 9), "flat", "carpet only", "DIMATOWN", ["GAN G SEA LANTERN", "DIMA"], 1203487165615579207),
        BigMapArt((10, 8), "flat", "carpet only", "Hausemaster should just delete the entire world of 2b2t",
                  ["GAN G SEA LANTERN"], 1203486991799549973),
        BigMapArt((15, 10), "flat", "carpet only", "yodieland", ["GAN G SEA LANTERN"], 1203486952855306330),
        BigMapArt((5, 8), "flat", "carpet only", "belle delphine", ["GAN G SEA LANTERN"], 1203486395583430758),
        BigMapArt((8, 4), "flat", "carpet only", "KING KRUST", ["GAN G SEA LANTERN"], 1203486365711466618),
        BigMapArt((6, 8), "flat", "carpet only", "Godfrey, First Elden Lord", ["GAN G SEA LANTERN"],
                  1203486235100708864),
        BigMapArt((8, 8), "flat", "carpet only", "scrunch", ["GAN G SEA LANTERN"], 1203486157409755236),
        BigMapArt((6, 6), "flat", "carpet only", "Starscourge Radahn", ["GAN G SEA LANTERN"], 1203486002094673970),
        BigMapArt((8, 4), "flat", "carpet only", "GT-Four", ["GAN G SEA LANTERN"], 1203485858896945242),
        BigMapArt((7, 7), "flat", "carpet only", "big luni", ["GAN G SEA LANTERN"], 1203485846972530738),
        BigMapArt((6, 8), "flat", "carpet only", "joycongodz 999", ["GAN G SEA LANTERN"], 1203485833827459142),
        BigMapArt((9, 5), "flat", "carpet only", "2b2t_Uncensored Mod Team", ["GAN G SEA LANTERN"],
                  1203485398043459615),
        BigMapArt((6, 6), "flat", "carpet only", "small luni", ["GAN G SEA LANTERN"], 1203485357887332382),
        BigMapArt((20, 20), "flat", "carpet only", "Hubble Ultra Deep Field (2004)", ["DuctTapeMessiah"],
                  1205328109579145296),
        BigMapArt((8, 4), "flat", "carpet only", "2.2", ["CrowTheBest", "WrityGD", "M1vae", "AdidasManS"],
                  1205328109579145296),
    ]

    def __init__(self, bot):
        self.bot = bot
        self.bot.help_command.cog = self

        # we sort by total maps (descending) and message id (-> message age - ascending)
        # because the ordering is opposite for the two, we invert the message id, so when reversed we get the ascending
        # order that we want. There is probably a more pythonic way to do this, but whatever.
        self.biggest_maps = sorted(self.biggest_maps, key=lambda x: (x.total_maps, x.message_id * -1), reverse=True)

    @commands.is_nsfw()
    @commands.command()
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
    @commands.command(aliases=["id"])
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

    @commands.command(aliases=["largest"])
    async def biggest(self, ctx, page: int = 1):
        """The biggest map art on 2b2t

        Parameters
        ----------
        page : int, optional
            The page number
        """
        max_page = math.ceil(len(self.biggest_maps) / 10)

        if 0 >= page or page > max_page:
            await ctx.reply(f"Page {page} is invalid.")
            return

        maps = self.biggest_maps[(page - 1) * 10:page * 10]
        ranks = {1: "🥇", 2: "🥈", 3: "🥉"}

        message = (
            "# Biggest map-art ever built on 2b2t:\n"
        )

        for (i, bigmap) in enumerate(maps):
            rank = i + 1 + (page - 1) * 10
            message += f"**{ranks.get(rank, f'{rank}:')}** {bigmap.line}\n"

        message += f"\n_Page {page}/{max_page} - use `!!biggest <n>` to see page n_"

        await ctx.send(message)

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
