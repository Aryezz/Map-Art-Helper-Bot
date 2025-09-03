import datetime
import json
import logging
import math
import traceback
from typing import Set, List

import discord
from discord.app_commands.checks import has_role
from discord.ext import commands, tasks
from discord.ext.commands import is_owner

import ai
import config
import sqla_db
from cogs import checks
from cogs.views import MapEntityEditorView
from map_archive_entry import MapArtArchiveEntry

logger = logging.getLogger("discord.map_archive")


class MapArchiveCommands(commands.Cog, name="Map Archive"):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.archive_channel: discord.TextChannel = self.bot.get_channel(config.map_archive_channel_id)
        self.bot_log_channel: discord.TextChannel = self.bot.get_channel(config.bot_log_channel_id)

    async def cog_load(self) -> None:
        await sqla_db.create_schema()

        if not config.dev_mode:
            self.update_archive.start()

    def cog_unload(self):
        self.update_archive.cancel()

    @has_role("staff")
    @commands.command()
    async def edit(self, ctx: commands.Context, *search_terms):
        async with sqla_db.Session() as db:
            query_builder = db.get_query_builder()

            for term in search_terms:
                query_builder.add_search_filter(term)

            results = await query_builder.execute()

        if len(results) == 0:
            await ctx.reply("no results for this search")
            return
        if len(results) > 1:
            await ctx.reply("multiple results for this search")
            return

        await ctx.send(view=MapEntityEditorView(ctx.author, results[0]))

    async def fix_attributes(self, entry: MapArtArchiveEntry):
        message = await self.archive_channel.fetch_message(entry.message_id)

        entry.author_id = message.author.id
        entry.create_date = message.created_at.replace(tzinfo=datetime.UTC)
        entry.image_url = message.attachments[0].url if len(message.attachments) > 0 else ""
        entry.flagged = any(attachment.is_spoiler() for attachment in message.attachments)

        return entry

    @tasks.loop(minutes=5)
    async def update_archive(self):
        try:
            async with sqla_db.Session() as db:
                fetch_from_timestamp = await db.get_latest_create_date()

            if fetch_from_timestamp is not None:
                messages = [message async for message in self.archive_channel.history(limit=50, after=fetch_from_timestamp, oldest_first=True)]
            else:
                messages = [message async for message in self.archive_channel.history(limit=50, oldest_first=True)]

            if len(messages) == 0:
                return

            ai_processed = await ai.process_messages(messages)

            final_entries: List[MapArtArchiveEntry] = []
            for entry in ai_processed:
                final_entries.append(await self.fix_attributes(entry))

            async with sqla_db.Session() as db:
                await db.add_maps(final_entries)

            if not config.dev_mode:
                await self.bot_log_channel.send(f"processed {len(messages)} messages, added {len(final_entries)} maps")
        except BaseException as e:
            logger.error("error while processing maps", exc_info=e)
            if not config.dev_mode:
                await self.bot_log_channel.send(f"error while processing maps: \n```{e}\n{traceback.format_exc()}```")

    @update_archive.before_loop
    async def before_updating_archive(self):
        await self.bot.wait_until_ready()

    @is_owner()
    @commands.command()
    async def import_map(self, ctx, msg_id: int):
        msg = await self.archive_channel.fetch_message(msg_id)
        processed = await ai.process_messages([msg])

        async with sqla_db.Session() as db:
            await db.add_maps(processed)

        await ctx.send(f"```{json.dumps(processed, indent=2)}```")

    @checks.is_in_bot_channel()
    @commands.command(aliases=["largest", "search"])
    async def biggest(self, ctx: commands.Context, *args):
        """The biggest map art on 2b2t

        Usage: !!biggest [args]

        Parameters
        ----------
        args : list, optional
            Page and filters to apply to the list of maps.
            To filter out flat maps, use `-f`,
            to filter out carpet-only maps, use `-c` or `-co`
        """

        is_search = ctx.invoked_with == "search"

        filter_args: List[str] = list(args)

        filter_flat_options: Set[str] = {"-f", "-flat"}
        filter_carpet_only_options: Set[str] = {"-c", "-co", "-carpet", "-carpetonly", "-carpet-only"}

        filter_flat_only = False
        filter_carpet_only = False
        filter_artists = []
        page = 1
        search_terms = []

        while len(filter_args) > 0:
            arg = filter_args.pop(0)

            if arg in filter_flat_options:
                filter_flat_only = True
            elif arg in filter_carpet_only_options:
                filter_carpet_only = True
            elif arg == "-n" and len(filter_args) >= 1:
                filter_artists.append(filter_args.pop(0))
            elif arg.isnumeric() and int(arg) < 100:
                page = int(arg)
            else:
                search_terms.append(arg)

        title_note = []

        async with sqla_db.Session() as db:
            query_builder = db.get_query_builder()

            # without any filters, the cutoff is 32 individual maps
            # => smaller maps only show up if you explicitly filter
            min_size = 32

            if filter_flat_only:
                # when filtering for non-flat maps, the default cutoff is 8 maps
                min_size = min(min_size, 8)
                query_builder.add_type_filter(sqla_db.MapArtType.FLAT)
                title_note.append("No flat maps")

            if filter_carpet_only:
                query_builder.add_palette_filter(sqla_db.MapArtPalette.CARPETONLY)
                title_note.append("No carpet-only maps")

            for artist in filter_artists:
                query_builder.add_artist_filter(artist)

            if len(filter_artists) > 0:
                # when filtering by artist, there is no minimum size
                min_size = min(min_size, 0)
                name_list = ", ".join(filter_artists[:-1]) + " and " + filter_artists[-1] if len(filter_artists) > 1 else filter_artists[0]
                title_note.append(f"by {name_list}")

            for search_term in search_terms:
                query_builder.add_search_filter(search_term)

            if len(search_terms) > 0 or is_search:
                # when searching, there is no minimum size
                min_size = 0

            if is_search:
                query_builder.order_by_date()
            else:
                query_builder.order_by_size()

            query_builder.add_size_filter(min_size)

            results = await query_builder.execute()

        max_page = math.ceil(len(results) / 10)

        if 0 >= page or page > max_page:
            await ctx.reply(f"No results")
            return

        page_entries = results[(page - 1) * 10:page * 10]
        ranks = {1: "🥇", 2: "🥈", 3: "🥉"}

        if is_search:
            title = "Search Results"
        else:
            title = f"Biggest map-art ever built on 2b2t{(" (" + ", ".join(title_note) + ")") if title_note else ""}"

        message = f"# {title}:\n"

        for (i, entry) in enumerate(page_entries):
            if is_search:
                message += entry.line + "\n"
            else:
                rank = i + 1 + (page - 1) * 10
                message += f"**{ranks.get(rank, f'{rank}:')}** {entry.line}\n"

        message += f"\n_Page {page}/{max_page}"
        filters_joined = (' ' + ' '.join(set(args) - {str(page)})) if args else ""
        if page < max_page:
            message += f" - use `{ctx.clean_prefix}{ctx.invoked_with} {page + 1}{filters_joined}` to see next page"
        elif page > 1:  # only show previous page hint if not on first page
            message += f" - use `{ctx.clean_prefix}{ctx.invoked_with} {page - 1}{filters_joined}` to see previous page"
        message += "_"  # end italics

        if len(message) <= 2000:
            await ctx.send(message)
        else:
            lines = message.split("\n")
            await ctx.send("\n".join(lines[:6]))
            await ctx.send("\n".join(lines[6:]))


async def setup(client):
    await client.add_cog(MapArchiveCommands(client))