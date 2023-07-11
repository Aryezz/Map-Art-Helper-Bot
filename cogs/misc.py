import hashlib
import re
import io
import random
from typing import *
from dataclasses import dataclass

import aiohttp
import discord
from discord.ext import commands
from PIL import Image

from cogs import exceptions

session = aiohttp.ClientSession()


@dataclass
class MapMetadata:
    id: int
    rotation: int = 0
    position: Tuple[int, int] = (0, 0)


@dataclass
class MapArtMaps:
    maps: List[MapMetadata]


class SingleMapArt(MapArtMaps):
    @classmethod
    async def convert(cls, ctx, map_id: str):
        if not map_id.isnumeric():
            raise commands.BadArgument("Map ID is not numeric")

        return cls(maps=[MapMetadata(id=int(map_id))])


class MultiMapRange(MapArtMaps):
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

        return cls(maps=map_ids)


class MultiMapList(MapArtMaps):
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

        return cls(maps=map_ids)


async def fetch_map(map_id: int) -> bytes:
    # v parameter is used for caching, using random value to avoid getting outdated images
    url = f"https://mapartwall.rebane2001.com/mapimg/map_{map_id!s}.png?v={random.randint(0, 999_999_999)}"

    async with session.get(url, ssl=False) as resp:
        if not resp.status == 200:
            raise commands.CommandError("Mapartwall responded with response status code " + str(resp.status))

        data = await resp.read()

        return data


async def generate_map(ctx, map_ids: MapArtMaps, upscale: bool = False) -> discord.File:
    blacklist = [  # blacklist for TOS maps to not get server banned
        "89be42fca8ecce7d821bf36d82d9ffd00157d5b5a943dd379141607412e316b9",
        "ae6d3a992c15ee9b4f004d9e52dde6ed65681a1c0830e35475ac39452b11377b",
        "440dbb039ff6f2d57c0a540c84f0d07e32687c295388be76ec88fca990fc553e",
        "780dcdcf480185c5823b5115c4acbdfb251b45cba5bc09dc533ea9640e75d1e2",
        "9846db0d5cdd13deeea480d36e88bdc263e22dbea0458d90a84e599341a7f5cb",
        "8f3289eec87009bdc6f191c9223b9e753bf6ce86cf5daa9927ae4f2221ae363a",
        "83e247b8454deaeffda10bb621af803853b2598ad633340e7233f20df0160d28",
    ]

    map_art_width = max(meta.position[0] for meta in map_ids.maps) + 1
    map_art_height = max(meta.position[1] for meta in map_ids.maps) + 1
    full_map = Image.new("RGBA", (map_art_width * 128, map_art_height * 128))
    map_cache: Dict[int, bytes] = {}

    for map_art in map_ids.maps:
        if map_art.id not in map_cache.keys():
            map_cache[map_art.id] = await fetch_map(map_art.id)

        if hashlib.sha256(map_cache[map_art.id]).hexdigest() in blacklist:
            raise exceptions.BlacklistedMapError(map_art.id, ctx.author)

        img = Image.open(io.BytesIO(map_cache[map_art.id])).convert("RGBA")

        if img.getextrema()[3][1] < 255:  # Map is completely transparent
            raise exceptions.TransparentMapError(map_art.id)

        if map_art.rotation:
            img = img.rotate(map_art.rotation * -90)

        full_map.paste(img, (map_art.position[0] * 128, map_art.position[1] * 128))

    if upscale:  # upscaling maps for better viewing in the discord client
        full_map = full_map.resize((full_map.width * 4, full_map.height * 4), Image.NEAREST)

    img_bytes = io.BytesIO()
    full_map.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return discord.File(img_bytes, "map.png")


class MiscCommands(commands.Cog, name="Misc"):
    """Miscellaneous commands"""
    def __init__(self, bot):
        self.bot = bot
        self.bot.help_command.cog = self

    @commands.is_nsfw()
    @commands.command()
    async def stitch(self, ctx, *, map_ids: Union[SingleMapArt, MultiMapRange, MultiMapList]):
        """
        Stitches together maps from mapartwall, map_ids has to be one of the following formats:
        * 1234-1239 3x2 (generates 2x2 map with the ids 1234-1238)
        * 1234,1235,1236;1237,1238,1239 (generates the same map, useful when the maps are not in order)
        * 1234,1234.1;1234.3,1234.2 (add periods after an id to rotate the map 1-3 times clockwise)
        """
        async with ctx.channel.typing():
            await ctx.send(file=await generate_map(ctx, map_ids))

    @commands.is_nsfw()
    @commands.command(aliases=["id"])
    async def map(self, ctx, map_id: SingleMapArt):
        """Sends a map from mapartwall"""
        async with ctx.channel.typing():
            await ctx.send(file=await generate_map(ctx, map_id, upscale=True))

    @map.error
    @stitch.error
    async def map_error(self, ctx, error):
        error = getattr(error, 'original', error)

        if isinstance(error, exceptions.TransparentMapError):
            await ctx.reply(f"Map {error.map_id!s} is empty.")
        elif isinstance(error, exceptions.BlacklistedMapError):
            print(str(error))
            return

    @commands.command(aliases=["largest"])
    async def biggest(self, ctx):
        """The biggest Map Art on 2b"""
        message = (
            "**Biggest Maps ever built on 2b2t:**\n"
            "27 x 16 (432 maps) [dual-layered, two-colour] - no comment by popstonia: "
            "https://discord.com/channels/349201680023289867/349277718954901514/910748616283545640\n"
            "21 x 12 (252 maps) [staircased, full colour] - Angel's Mirror by KevinKC2014: "
            "https://discord.com/channels/349201680023289867/349277718954901514/953371453447884851\n"
            "11 x 11 (121 maps) [flat, 98.7% carpet] - Mapopoly by T Gang: "
            "https://discord.com/channels/349201680023289867/349277718954901514/957248581339844668\n"
            "8 x 8 (64 maps) [dual-layered, carpet only] - ponystonia by popstonia: "
            "https://discord.com/channels/349201680023289867/349277718954901514/954851826770018364\n"
            "8 x 8 (64 maps) [flat + terrain, full colour] - Sky Masons by The Spawn Masons: "
            "https://discord.com/channels/349201680023289867/349277718954901514/916099357823103038\n"
            "9 x 6 (54 maps) [flat, two-colour] - Abaddons Last Art by Phi, Albatros and Tae: "
            "https://discord.com/channels/349201680023289867/349277718954901514/650500181573500928\n"
            "8 x 5 (40 maps) [flag, full colour] - Deathly Hallows by Aryezz, IronException, THCFree and Sanku: "
            "https://discord.com/channels/349201680023289867/349277718954901514/859364782891991040\n"
            "8 x 4 (32 maps) [flat, full colour] - Gotta Catch Em' All by Harri: "
            "https://discord.com/channels/349201680023289867/349277718954901514/616841031605944360"
        )

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
            self.bot.reload_extension(extension)

        await ctx.send("reloaded all cogs")


async def setup(client):
    await client.add_cog(MiscCommands(client))
