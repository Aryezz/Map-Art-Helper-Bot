import datetime
import logging
import math
import traceback
from typing import Optional, Callable, Annotated

import discord
from discord import DiscordException, ui
from discord.ext.commands import has_role, is_owner
from discord.ext import commands, tasks

import ai
import config
import sqla_db
from ai import MapArtLLMOutput
from cogs import checks
from cogs.search import SearchArguments, SearchArgumentConverter, SearchResults, search_entries
from cogs.views import MapEntityEditorView
from map_archive_entry import MapArtArchiveEntry

logger = logging.getLogger("discord.map_archive")


def is_staff_or_owner():
    return commands.check_any(has_role("staff"), is_owner())


def get_detail_view(entry: MapArtArchiveEntry):
    view = ui.LayoutView()
    thumbnail_url = entry.image_url or "https://minecraft.wiki/images/Barrier_%28held%29_JE2_BE2.png"
    header = ui.Section(
        ui.TextDisplay(f"# {entry.name}\n[Jump to message in archive]({entry.link})"),
        accessory=ui.Thumbnail(thumbnail_url, spoiler=entry.flagged)
    )
    view.add_item(header)
    view.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
    view.add_item(
        ui.TextDisplay(discord.utils.escape_mentions(
            f"### Size\n{entry.width} x {entry.height} ({entry.total_maps} {"map" if entry.total_maps == 1 else "maps"})\n" +
            f"### Artists\n" + "\n".join(f"* {artist}" for artist in entry.artists) + "\n" +
            f"### Type\n{entry.map_type.value}\n"
            f"### Palette\n{entry.palette.value}\n"
            f"### Notes\n" +
            ("\n".join("> " + line for line in entry.notes.split("\n")) if entry.notes else "-"))
        )
    )
    return view


async def format_entry_list(ctx: commands.Context, search_results: SearchResults, title: str,
                            line_formatter: Callable[[int, MapArtArchiveEntry], str] = lambda _,
                                                                                              entry: entry.line,
                            page_size: int = 10) -> str:
    max_page = math.ceil(len(search_results.results) / page_size)

    page_entries = search_results.results[(search_results.page - 1) * page_size:search_results.page * page_size]

    message = f"# {title}:\n"

    lines = [line_formatter(i, entry) for (i, entry) in enumerate(page_entries)]
    message += "\n".join(lines)

    page_info = f"Page {search_results.page}/{max_page}, {len(search_results.results)} {'results' if len(search_results.results) != 1 else 'result'}"
    command_help = ""

    filters_joined = (' ' + ' '.join(search_results.non_page_args)) if search_results.non_page_args else ""
    if search_results.page < max_page:
        command_help = f" - use_ `{ctx.clean_prefix}{ctx.invoked_with} {search_results.page + 1}{filters_joined}` _to see next page"
    elif search_results.page > 1:  # only show previous page hint if not on first page
        command_help = f" - use_ `{ctx.clean_prefix}{ctx.invoked_with} {search_results.page - 1}{filters_joined}` _to see previous page"

    message += f"\n\n-# _{page_info}{command_help}_"
    return message


class MapArchiveCommands(commands.Cog, name="Map Archive"):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.archive_channel: discord.TextChannel = self.bot.get_channel(config.map_archive_channel_id)
        self.bot_log_channel: discord.TextChannel = self.bot.get_channel(config.bot_log_channel_id)
        self.cancel_queue: set[int] = set()

    async def cog_load(self) -> None:
        await sqla_db.create_schema()

        if not config.dev_mode:
            self.update_archive.start()

    def cog_unload(self):
        self.update_archive.cancel()

    async def fix_attributes(self, entry: MapArtLLMOutput) -> Optional[MapArtArchiveEntry]:
        message = await self.archive_channel.fetch_message(entry.message_id)

        fixed_artists = []
        for artist in entry.artists:
            fixed_artist = artist.replace("\r", "").replace("\n", "").strip()
            if fixed_artist:
                fixed_artists.append(fixed_artist)

        return MapArtArchiveEntry(
            width=entry.width,
            height=entry.height,
            map_type=entry.map_type,
            palette=entry.palette,
            name=entry.name,
            artists=fixed_artists,
            notes=entry.notes,
            message_id=entry.message_id,

            author_id=message.author.id,
            create_date=message.created_at.replace(tzinfo=datetime.UTC),
            image_url=message.attachments[0].url if len(message.attachments) > 0 else "",
            flagged=any(attachment.is_spoiler() for attachment in message.attachments),
        )

    @tasks.loop(minutes=90)
    async def update_archive(self):
        try:
            async with sqla_db.Session() as db:
                fetch_from_timestamp = await db.get_latest_create_date()

            if fetch_from_timestamp is not None:
                messages = [message async for message in
                            self.archive_channel.history(limit=50, after=fetch_from_timestamp, oldest_first=True)]
            else:
                messages = [message async for message in self.archive_channel.history(limit=50, oldest_first=True)]

            if len(messages) == 0:
                return

            ai_processed: list[MapArtLLMOutput] = await ai.process_messages(messages)

            try:
                final_entries: list[MapArtArchiveEntry] = [await self.fix_attributes(entry) for entry in ai_processed]
            except DiscordException:
                logger.error("error in LLM returned data, skipping")
                await self.bot_log_channel.send("error in LLM returned data, skipping")
                return

            async with sqla_db.Session() as db:
                await db.add_maps(final_entries)

            if not config.dev_mode:
                await self.bot_log_channel.send(f"processed {len(messages)} messages, added {len(final_entries)} maps")

                for entry in final_entries:
                    await self.bot_log_channel.send(view=get_detail_view(entry))

        except BaseException as error:
            logger.error("error while processing maps", exc_info=error)
            if not config.dev_mode:
                tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
                message = f"An error occurred while importing maps from the archive:\n```py\n{tb}\n```"

                await self.bot_log_channel.send(message)

    @update_archive.before_loop
    async def before_updating_archive(self):
        await self.bot.wait_until_ready()

    async def get_entry_message_content(self, entry: MapArtArchiveEntry) -> str:
        return (await self.archive_channel.fetch_message(entry.message_id)).clean_content

    @is_staff_or_owner()
    @commands.command(aliases=["e", "ea", "editall"], hidden=True, rest_is_raw=True)
    async def edit(self, ctx: commands.Context, *, search_args: Annotated[
        SearchArguments, SearchArgumentConverter(default_min_size=0, default_order_by="date")]):
        search_results = await search_entries(search_args)
        results = search_results.results[(search_results.page - 1) * 10:]

        if len(results) == 0:
            await ctx.reply("no results for this search")
            return
        if ctx.invoked_with in ("e", "edit"):
            # normal edit semantics
            if len(results) > 1:
                await ctx.reply(
                    f"multiple results for this search, use `{ctx.clean_prefix}editall` to edit multiple maps")
                return

            try:
                message_content = await self.get_entry_message_content(results[0])
            except discord.NotFound:
                message_content = "(!) Message not found"
            await ctx.send(view=MapEntityEditorView(ctx.author, results[0], message_content))
        elif ctx.invoked_with in ("ea", "editall"):
            # mass edit semantics
            self.cancel_queue.discard(ctx.author.id)
            for entry in results:
                if ctx.author.id in self.cancel_queue:
                    self.cancel_queue.discard(ctx.author.id)
                    return

                try:
                    message_content = await self.get_entry_message_content(entry)
                except discord.NotFound:
                    message_content = "(!) Message not found"
                editor_view = MapEntityEditorView(ctx.author, entry, message_content)
                await ctx.send(view=editor_view)
                await editor_view.wait()

    @is_staff_or_owner()
    @commands.command(hidden=True)
    async def cancel(self, ctx: commands.Context):
        self.cancel_queue.add(ctx.author.id)
        await ctx.reply("multi-edit cancelled", ephemeral=True)

    @is_staff_or_owner()
    @commands.command(hidden=True)
    async def import_map(self, ctx, message: discord.Message):
        msg = await self.archive_channel.fetch_message(message.id)

        ai_processed: list[MapArtLLMOutput] = await ai.process_messages([msg])

        try:
            final_entries: list[MapArtArchiveEntry] = [await self.fix_attributes(entry) for entry in ai_processed]
        except DiscordException:
            logger.error("error in LLM returned data, skipping")
            await ctx.send("error in LLM returned data, skipping")
            return

        async with sqla_db.Session() as db:
            await db.add_maps(final_entries)

            await ctx.send(f"processed 1 message, added {len(final_entries)} maps")

            for entry in final_entries:
                await self.bot_log_channel.send(view=get_detail_view(entry))

    @is_staff_or_owner()
    @commands.command(hidden=True)
    async def reimport_map(self, ctx, message: discord.Message):
        msg = await self.archive_channel.fetch_message(message.id)

        async with sqla_db.Session() as db:
            query_builder = db.get_query_builder()
            query_builder.add_search_filter([str(msg.id)])

            previous_entries = await query_builder.execute()

            if len(previous_entries) != 1:
                logger.error("not exactly one entry returned, skipping")
                await ctx.send("not exactly one entry returned, skipping")
                return

            previous_entry = previous_entries[0]

        ai_processed: list[MapArtLLMOutput] = await ai.process_messages([msg])

        try:
            final_entries: list[MapArtArchiveEntry] = [await self.fix_attributes(entry) for entry in ai_processed]
        except DiscordException:
            logger.error("error in LLM returned data, skipping")
            await ctx.send("error in LLM returned data, skipping")
            return

        async with sqla_db.Session() as db:
            await db.delete_maps([previous_entry])
            await db.add_maps(final_entries)

            await ctx.send(f"deleted 1 entry, processed 1 message, added {len(final_entries)} maps")

            for entry in final_entries:
                await self.bot_log_channel.send(view=get_detail_view(entry))

    @is_staff_or_owner()
    @commands.command(hidden=True)
    async def rename_artist(self, ctx: commands.Context, old_name: str, new_name: str):
        async with sqla_db.Session() as db:
            query_builder = db.get_query_builder()
            query_builder.add_artist_filter([old_name])

            entries = await query_builder.execute()

            for entry in entries:
                entry.artists.remove(old_name)
                entry.artists.append(new_name)

            await db.add_maps(entries)

        await ctx.reply("renamed")

    @checks.is_in_bot_channel()
    @commands.command(rest_is_raw=True, aliases=["s"])
    async def search(self, ctx: commands.Context, *, search_args: Annotated[
        SearchArguments, SearchArgumentConverter(default_min_size=0, default_order_by="date")]):
        """Search map arts in the archive

        Usage: !!search [search_args]

        Parameters
        ----------
        search_args : list, optional
            keyword value pairs in the format key:value or plain search terms.
            recognized keys: page, artist, type, palette, size and order.
            use "-" to negate arguments, e.g. -type:flat to filter flat maps.
        """

        try:
            search_results = await search_entries(search_args)
        except ValueError as error:
            await ctx.send(str(error))
            return

        if len(search_results.results) == 1:
            await ctx.send(view=get_detail_view(search_results.results[0]))
            return

        message = await format_entry_list(ctx, search_results, title="Search Results")

        if len(message) <= 2000:
            await ctx.send(message)
        else:
            lines = message.split("\n")
            await ctx.send("\n".join(lines[:6]))
            await ctx.send("\n".join(lines[6:]))

    @checks.is_in_bot_channel()
    @commands.command()
    async def random(self, ctx: commands.Context):
        async with sqla_db.Session() as db:
            entry = await db.get_random_map()

        if entry is not None:
            await ctx.send(view=get_detail_view(entry))

    @checks.is_in_bot_channel()
    @commands.command(aliases=["largest"], rest_is_raw=True)
    async def biggest(self, ctx: commands.Context, *, search_args: Annotated[
        SearchArguments, SearchArgumentConverter(default_min_size=32, default_order_by="size")]):
        """The biggest map art on 2b2t

        Usage: !!biggest [search_args]

        Parameters
        ----------
        search_args : list, optional
            keyword value pairs in the format key:value or plain search terms.
            recognized keys: page, artist, type, palette, size and order.
            use "-" to negate arguments, e.g. -type:flat to filter flat maps.
        """

        try:
            search_results = await search_entries(search_args)
        except ValueError as error:
            await ctx.send(str(error))
            return

        if len(search_results.results) == 1:
            await ctx.send(view=get_detail_view(search_results.results[0]))
            return

        title = "Biggest map-art ever built on 2b2t"

        if search_args.non_page_args:
            title = f"{title} (filtered)"

        ranks = {1: "🥇", 2: "🥈", 3: "🥉"}

        def rank_formatter(i: int, entry: MapArtArchiveEntry):
            rank = i + 1 + (search_results.page - 1) * 10
            return f"**{ranks.get(rank, f'{rank}:')}** {entry.line}"

        message = await format_entry_list(ctx, search_results, title=title, line_formatter=rank_formatter)

        if len(message) <= 2000:
            await ctx.send(message)
        else:
            lines = message.split("\n")
            await ctx.send("\n".join(lines[:6]))
            await ctx.send("\n".join(lines[6:]))


async def setup(client):
    await client.add_cog(MapArchiveCommands(client))
