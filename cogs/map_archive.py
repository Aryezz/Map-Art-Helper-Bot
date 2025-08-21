import math
from typing import Set

from discord.ext import commands
from discord.ext.commands import is_owner


import sqla_db
from cogs import checks


class MapArchiveCommands(commands.Cog, name="Map Archive"):
    def __init__(self, bot):
        self.bot = bot

        # DB connection, will be set in cog_load()
        self.session = None

    async def cog_load(self):
        self.session = await sqla_db.get_session()

        # check archive for any new messages not in the DB yet
        pass

    @is_owner()
    @commands.command()
    async def load_data(self, ctx):
        await sqla_db.load_data(self.session)

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
        query_builder = sqla_db.MapArtQueryBuilder(self.session)

        # without any filters, the cutoff is 32 individual maps
        # => smaller maps only show up if you explicitly filter
        if len(filters) == 0 or len(name_filter) > 0:
            query_builder.add_size_filter(32)

        if any(f in filters for f in filter_flat_options):
            query_builder.add_size_filter(8)
            query_builder.add_type_filter(sqla_db.MapArtType.FLAT)
            title_note.append("No flat maps")

        if any(f in filters for f in filter_carpet_only_options):
            query_builder.add_size_filter(32)
            query_builder.add_palette_filter(sqla_db.MapArtPalette.CARPETONLY)
            title_note.append("No carpet-only maps")

        for artist in name_filter:
            query_builder.add_artist_filter(artist)

        if name_filter:
            name_list = ", ".join(name_filter[:-1]) + " and " + name_filter[-1] if len(name_filter) > 1 else name_filter[0]
            title_note.append(f"by {name_list}")

        found_maps = await query_builder.execute()

        max_page = math.ceil(len(found_maps) / 10)

        if 0 >= page or page > max_page:
            await ctx.reply(f"No results")
            return

        maps = found_maps[(page - 1) * 10:page * 10]
        ranks = {1: "🥇", 2: "🥈", 3: "🥉"}

        message = f"# Biggest map-art ever built on 2b2t{(" (" + ", ".join(title_note) + ")") if title_note else ""}:\n"

        for (i, bigmap) in enumerate(maps):
            await self.session.refresh(bigmap)

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