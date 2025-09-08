import datetime
import logging
import math
import re
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Literal, Callable, Annotated

import discord
from discord import DiscordException, ui
from discord.app_commands.checks import has_role
from discord.ext import commands, tasks
from discord.ext.commands import is_owner

import ai
import config
import sqla_db
from ai import MapArtLLMOutput
from cogs import checks
from cogs.views import MapEntityEditorView
from map_archive_entry import MapArtArchiveEntry, MapArtType, MapArtPalette

logger = logging.getLogger("discord.map_archive")

order_by_arg = Literal["size", "date"]


class MixedArgsConverter(commands.Converter):
    async def convert(self, ctx, argument) -> tuple[list[str], dict[str, list[str]]]:
        args = []
        kwargs = defaultdict(list)

        while argument:
            # keyword argument with quoted value, e.g. key: "value quoted"
            if match := re.match(r"(?P<key>\S+)\s*:\s*\"(?P<value>([^\"\\]|\\.)*)\"", argument):
                key = match.group("key")
                value = re.sub(r"\\(.)", r"\1", match.group("value"))
                kwargs[key].append(value)
                argument = argument[match.end():].lstrip()
            # keyword argument with plain value, e.g. key: value
            elif match := re.match(r"(?P<key>\S+)\s*:\s*(?P<value>\S+)", argument):
                key = match.group("key")
                value = match.group("value")
                kwargs[key].append(value)
                argument = argument[match.end():].lstrip()
            # argument with quoted value, e.g. "value quoted"
            elif match := re.match(r"\"(?P<value>([^\"\\]|\\.)*)\"", argument):
                args.append(re.sub(r"\\(.)", r"\1", match.group("value")))
                argument = argument[match.end():].lstrip()
            # argument with plain value, e.g. value
            elif match := re.match(r"(?P<value>\S*)", argument):
                args.append(match.group("value"))
                argument = argument[match.end():].lstrip()
            else:
                raise ValueError(f"cannot continue parsing `{argument}`")

        return args, kwargs


@dataclass
class SearchArguments:
    included_types: list[MapArtType] = field(default_factory=list)
    excluded_types: list[MapArtType] = field(default_factory=list)
    included_palettes: list[MapArtPalette] = field(default_factory=list)
    excluded_palettes: list[MapArtPalette] = field(default_factory=list)
    included_artists: list[str] = field(default_factory=list)
    excluded_artists: list[str] = field(default_factory=list)
    included_keywords: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)

    min_size: int | None = None
    max_size: int | None = None

    order_by: order_by_arg = None

    filter_duplicates: bool = False
    page: int | None = None
    non_page_args: list[str] = field(default_factory=list)


class SearchArgumentConverter(MixedArgsConverter):
    filter_flat_options: set[str] = {"-f", "-flat"}
    filter_carpet_only_options: set[str] = {"-c", "-co", "-carpet", "-carpetonly", "-carpet-only"}

    def __init__(self, default_min_size: int=0, default_order_by: order_by_arg= "date"):
        super().__init__()

        self.default_min_size = default_min_size
        self.default_order_by = default_order_by

    def parse_size_arg(self, arg: str, search_args: SearchArguments) -> bool:
        if match := re.match(r"(?P<qualifier>[><]=?|=)(?P<size>\d+)", arg):
            size = int(match.group("size"))
            qualifier = match.group("qualifier")

            if qualifier == ">":
                size += 1
            elif qualifier == "<":
                size -= 1

            if size < 1:
                raise ValueError("Invalid size argument")

            if qualifier.startswith(">") or qualifier == "=":
                if search_args.min_size is not None:
                    raise ValueError("multiple min-size arguments encountered")

                search_args.min_size = size
            if qualifier.startswith("<") or qualifier == "=":
                if search_args.max_size is not None:
                    raise ValueError("multiple max-size arguments encountered")

                search_args.max_size = size

            return True
        return False

    async def convert(self, ctx, argument):
        search_arguments = SearchArguments()

        cleaned_args = re.sub(r"https?://discord.com/channels/\d+/\d+/(\d+)", r"\1", argument)

        args, kwargs = await super().convert(ctx, cleaned_args)

        for arg in args:
            if re.fullmatch(r"-?\d{1,3}", arg):
                if search_arguments.page is not None:
                    raise ValueError("multiple page arguments encountered")

                search_arguments.page = int(arg)
                continue

            if self.parse_size_arg(arg, search_arguments):
                continue

            search_arguments.non_page_args.append(arg)

            if arg in self.filter_flat_options:
                search_arguments.excluded_types.append(MapArtType.FLAT)
                self.default_min_size = min(self.default_min_size, 8)
            elif arg in self.filter_carpet_only_options:
                search_arguments.excluded_palettes.append(MapArtPalette.CARPETONLY)
            elif arg == "-dup":
                search_arguments.filter_duplicates = True
            else:
                self.default_min_size = min(self.default_min_size, 0)
                if arg.startswith("-"):
                    search_arguments.excluded_keywords.append(arg[1:])
                else:
                    search_arguments.included_keywords.append(arg)

        for (key, value) in kwargs.items():
            if exclude := key.startswith("-"):
                key = key[1:]

            if "page".startswith(key):
                if exclude:
                    raise ValueError("cannot use exclusion for argument `page`")
                if search_arguments.page is not None:
                    raise ValueError("multiple page arguments encountered")

                search_arguments.page = int(value[-1])
            elif "artist".startswith(key):
                if exclude:  search_arguments.excluded_artists.extend(value)
                else:        search_arguments.included_artists.extend(value)
            elif "type".startswith(key):
                map_types = [MapArtType[t] for t in value]
                if exclude:  search_arguments.excluded_types.extend(map_types)
                else:        search_arguments.included_types.extend(map_types)
            elif "palette".startswith(key):
                map_palettes = [MapArtPalette[p] for p in value]
                if exclude:  search_arguments.excluded_palettes.extend(map_palettes)
                else:        search_arguments.included_palettes.extend(map_palettes)
            elif "size".startswith(key):
                if exclude:
                    raise ValueError("cannot use exclusion for argument `size`")

                for size_arg in value:
                    self.parse_size_arg(size_arg, search_arguments)

        if search_arguments.page is None:
            search_arguments.page = 1
        if search_arguments.min_size is None:
            search_arguments.min_size = self.default_min_size
        if search_arguments.order_by is None:
            search_arguments.order_by = self.default_order_by

        return search_arguments


@dataclass
class SearchResults:
    page: int
    non_page_args: list[str]
    results: list[MapArtArchiveEntry] = field(default_factory=list)

    def max_page(self, page_size: int = 10):
        return math.ceil(len(self.results) / page_size)

    def page_valid(self, page_size: int = 10):
        return 0 < self.page <= self.max_page(page_size)


async def search_entries(query: SearchArguments) -> SearchResults:
    results = SearchResults(query.page, query.non_page_args)

    async with sqla_db.Session() as db:
        query_builder = db.get_query_builder()

        query_builder.add_type_filter(include=query.included_types, exclude=query.excluded_types)
        query_builder.add_palette_filter(include=query.included_palettes, exclude=query.excluded_palettes)

        if query.filter_duplicates:
            query_builder.add_duplicate_filter()

        query_builder.add_artist_filter(include=query.included_artists, exclude=query.excluded_artists)
        query_builder.add_search_filter(include=query.included_keywords, exclude=query.excluded_keywords)

        query_builder.order_by(query_builder.order_by)

        query_builder.add_size_filter(min_size=query.min_size, max_size=query.max_size)

        results.results = await query_builder.execute()

    if len(results.results) == 0:
        raise ValueError(f"No results")

    if len(results.results) >= 2 and not results.page_valid():
        raise ValueError(f"Invalid Page, select a page between 1 and {results.max_page()}")

    return results


def get_detail_view(entry):
    view = ui.LayoutView()
    thumbnail_url = entry.image_url or "https://minecraft.wiki/images/Barrier_%28held%29_JE2_BE2.png"
    header = ui.Section(
        ui.TextDisplay(f"# {entry.name}\n[Jump to message in archive]({entry.link})"),
        accessory=ui.Thumbnail(thumbnail_url, spoiler=entry.flagged)
    )
    view.add_item(header)
    view.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
    view.add_item(
        ui.TextDisplay(
            f"### Size\n{entry.width} x {entry.height} ({entry.total_maps} {"map" if entry.total_maps == 1 else "maps"})\n" +
            f"### Artists\n" + "\n".join(f"* {artist}" for artist in entry.artists) + "\n" +
            f"### Type\n{entry.map_type.value}\n"
            f"### Palette\n{entry.palette.value}\n"
            f"### Notes\n" +
            ("\n".join("> " + line for line in entry.notes.split("\n")) if entry.notes else "-")
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

    page_info = f"Page {search_results.page}/{max_page}"
    command_help = ""

    filters_joined = (' ' + ' '.join(search_results.non_page_args)) if search_results.non_page_args else ""
    if search_results.page < max_page:
        command_help = f" - use `{ctx.clean_prefix}{ctx.invoked_with} {search_results.page + 1}{filters_joined}` to see next page"
    elif search_results.page > 1:  # only show previous page hint if not on first page
        command_help = f" - use `{ctx.clean_prefix}{ctx.invoked_with} {search_results.page - 1}{filters_joined}` to see previous page"

    message += f"\n\n_{page_info} {command_help}_"
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

        return MapArtArchiveEntry(
            width=entry.width,
            height=entry.height,
            map_type=entry.map_type,
            palette=entry.palette,
            name=entry.name,
            artists=entry.artists,
            notes=entry.notes,
            message_id=entry.message_id,

            author_id=message.author.id,
            create_date=message.created_at.replace(tzinfo=datetime.UTC),
            image_url=message.attachments[0].url if len(message.attachments) > 0 else "",
            flagged=any(attachment.is_spoiler() for attachment in message.attachments),
        )

    @tasks.loop(minutes=5)
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
        except BaseException as error:
            logger.error("error while processing maps", exc_info=error)
            if not config.dev_mode:
                tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
                message = f"An error occurred while importing maps from the archive:\n```py\n{tb}\n```"

                await self.bot_log_channel.send(message)

    @update_archive.before_loop
    async def before_updating_archive(self):
        await self.bot.wait_until_ready()

    @has_role("staff")
    @commands.command(aliases=["e", "ea", "editall"])
    async def edit(self, ctx: commands.Context, search_terms: Annotated[
        SearchArguments, SearchArgumentConverter(default_min_size=0, default_order_by="date")]):
        search_results = await search_entries(search_terms)
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

            await ctx.send(view=MapEntityEditorView(ctx.author, results[0]))
        elif ctx.invoked_with in ("ea", "editall"):
            # mass edit semantics
            self.cancel_queue.discard(ctx.author.id)
            for entry in results:
                if ctx.author.id in self.cancel_queue:
                    self.cancel_queue.discard(ctx.author.id)
                    return
                editor_view = MapEntityEditorView(ctx.author, entry)
                await ctx.send(view=editor_view)
                await editor_view.wait()

    @has_role("staff")
    @commands.command()
    async def cancel(self, ctx: commands.Context):
        self.cancel_queue.add(ctx.author.id)
        await ctx.reply("multi-edit cancelled", ephemeral=True)

    @is_owner()
    @commands.command()
    async def import_map(self, ctx, message: discord.Message):
        msg = await self.archive_channel.fetch_message(message.id)

        ai_processed: list[MapArtLLMOutput] = await ai.process_messages([msg])

        try:
            final_entries: list[MapArtArchiveEntry] = [await self.fix_attributes(entry) for entry in ai_processed]
        except DiscordException:
            logger.error("error in LLM returned data, skipping")
            await ctx.send.send("error in LLM returned data, skipping")
            return

        async with sqla_db.Session() as db:
            await db.add_maps(final_entries)

            if not config.dev_mode:
                await ctx.send(f"processed 1 message, added {len(final_entries)} maps")

    @checks.is_in_bot_channel()
    @commands.command()
    async def search(self, ctx: commands.Context, *, search_args: Annotated[
        SearchArguments, SearchArgumentConverter(default_min_size=0, default_order_by="date")]):
        """Search map arts in the archive

        Usage: !!search [args]

        Parameters
        ----------
        search_args : list, optional
            Page and filters to apply to the list of maps.
            To filter out flat maps, use `-f`,
            to filter out carpet-only maps, use `-c` or `-co`,
            to filter maps by a specific artist, use `-n <name>`
        """

        try:
            search_results = await search_entries(search_args)
        except ValueError as error:
            await ctx.send(str(error))
            return

        message = await format_entry_list(ctx, search_results, title="Search Results")

        if len(search_results.results) == 1:
            await ctx.send(view=get_detail_view(search_results.results[0]))
            return

        if len(message) <= 2000:
            await ctx.send(message)
        else:
            lines = message.split("\n")
            await ctx.send("\n".join(lines[:6]))
            await ctx.send("\n".join(lines[6:]))

    @checks.is_in_bot_channel()
    @commands.command(aliases=["largest"])
    async def biggest(self, ctx: commands.Context, args: Annotated[
        SearchArguments, SearchArgumentConverter(default_min_size=32, default_order_by="size")]):
        """The biggest map art on 2b2t

        Usage: !!biggest [args]

        Parameters
        ----------
        args : list, optional
            Page and filters to apply to the list of maps.
            To filter out flat maps, use `-f`,
            to filter out carpet-only maps, use `-c` or `-co`,
            to filter maps by a specific artist, use `-n <name>`
        """

        try:
            search_results = await search_entries(args)
        except ValueError as error:
            await ctx.send(str(error))
            return

        if len(search_results.results) == 1:
            await ctx.send(view=get_detail_view(search_results.results[0]))
            return

        title = "Biggest map-art ever built on 2b2t"
        title_note = []

        if search_results.filter_flat_only:
            title_note.append("No flat maps")

        if search_results.filter_carpet_only:
            title_note.append("No carpet-only maps")

        if search_results.filter_duplicates:
            title_note.append("Duplicates")

        if title_note:
            title = f"{title} ({", ".join(title_note)})"

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
