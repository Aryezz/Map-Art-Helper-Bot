import math
from typing import List, Set

import aiosqlite
from discord.ext import commands
from discord.ext.commands import is_owner

import db
from cogs import checks
from cogs.map_art import BigMapArt


class MapArchiveCommands(commands.Cog, name="Map Archive"):
    def __init__(self, bot):
        self.bot = bot

        # DB connection, will be set in cog_load()
        self.db = None

    async def cog_load(self):
        self.db = await aiosqlite.connect("map_art.db")

        # check archive for any new messages not in the DB yet
        pass

    @is_owner()
    @commands.command()
    async def create_schema(self, ctx):
        await db.create_schema(self.db)
        await db.load_data(self.db)

        await ctx.reply("schema created")

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
        maps_to_consider: List[BigMapArt] = await db.get_big_maps(self.db)

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



async def setup(client):
    await client.add_cog(MapArchiveCommands(client))