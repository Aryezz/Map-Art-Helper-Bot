import io
import json
import math
from typing import Set

import discord
from discord.app_commands.checks import has_role
from discord.ext import commands, tasks
from discord.ext.commands import is_owner

import ai
import config
import sqla_db
from cogs import checks


class MapArchiveCommands(commands.Cog, name="Map Archive"):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.archive_channel: discord.TextChannel = self.bot.get_channel(config.map_archive_channel_id)
        self.update_archive.start()

    def cog_unload(self):
        self.update_archive.cancel()

    @is_owner()
    @commands.command()
    async def import_map(self, ctx, msg_id: int):
        msg = await self.archive_channel.fetch_message(msg_id)
        processed = await ai.process_messages([msg])

        async with sqla_db.Session() as db:
            await db.add_maps(processed)

        await ctx.send(f"```{json.dumps(processed, indent=2)}```")

    @has_role("staff")
    @commands.command()
    async def search(self, ctx, *search_terms):
        async with sqla_db.Session() as db:
            query_builder = db.get_query_builder()

            for term in search_terms:
                query_builder.add_search_filter(term)

            results = await query_builder.execute()

        json_data = [map_art.json for map_art in results]
        json_output = json.dumps(json_data, indent=2)

        if len(json_output) + 6 > 2000:
            file = io.StringIO(json_output)
            await ctx.send(file=discord.File(file, "results.txt"))
        else:
            await ctx.send(f"```{json_output}```")

    @has_role("staff")
    @commands.command()
    async def update(self, ctx, *, map_entries: str):
        map_entries = map_entries.strip("`\n")

        entries = json.loads(map_entries)

        async with sqla_db.Session() as db:
            await db.add_maps(entries)

        await ctx.send("done")


    @tasks.loop(minutes=5)
    async def update_archive(self):
        async with sqla_db.Session() as db:
            latest_entry_message = await db.get_latest_message_id()

        if latest_entry_message is not None:
            latest_message = await self.archive_channel.fetch_message(latest_entry_message)
            fetch_from_timestamp = latest_message.created_at
            messages = [message async for message in self.archive_channel.history(limit=50, after=fetch_from_timestamp, oldest_first=True)]
        else:
            messages = [message async for message in self.archive_channel.history(limit=50, oldest_first=True)]

        if len(messages) == 0:
            return

        processed = await ai.process_messages(messages)

        async with sqla_db.Session() as db:
            await db.add_maps(processed)

    @update_archive.before_loop
    async def before_updating_archive(self):
        await self.bot.wait_until_ready()

    @checks.is_in_bot_channel()
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

        async with sqla_db.Session() as db:
            query_builder = db.get_query_builder()

            # without any filters, the cutoff is 32 individual maps
            # => smaller maps only show up if you explicitly filter
            min_size = 32

            if any(f in filters for f in filter_flat_options):
                # when filtering for non-flat maps, the default cutoff is 8 maps
                min_size = min(min_size, 8)
                query_builder.add_type_filter(sqla_db.MapArtType.FLAT)
                title_note.append("No flat maps")

            if any(f in filters for f in filter_carpet_only_options):
                query_builder.add_palette_filter(sqla_db.MapArtPalette.CARPETONLY)
                title_note.append("No carpet-only maps")

            for artist in name_filter:
                query_builder.add_artist_filter(artist)

            if name_filter:
                # when filtering by artist, there is no minimum size
                min_size = min(min_size, 0)
                name_list = ", ".join(name_filter[:-1]) + " and " + name_filter[-1] if len(name_filter) > 1 else name_filter[0]
                title_note.append(f"by {name_list}")

            query_builder.add_size_filter(min_size)

            found_maps = await query_builder.execute()

        max_page = math.ceil(len(found_maps) / 10)

        if 0 >= page or page > max_page:
            await ctx.reply(f"No results")
            return

        maps = found_maps[(page - 1) * 10:page * 10]
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