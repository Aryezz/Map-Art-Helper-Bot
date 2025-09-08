import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from discord.ext import commands

import sqla_db
from map_archive_entry import MapArtType, MapArtPalette, MapArtArchiveEntry

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


def parse_size_arg(arg: str, search_args: SearchArguments) -> bool:
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


def get_map_type(type_str: str) -> MapArtType | None:
    """Returns the best effort mapping of the provided string to a MapArtType"""
    if type_str.upper() in MapArtType:
        return MapArtType(type_str.upper())

    for map_type in MapArtType:
        if (map_type.value.lower() == type_str.lower() or
            map_type.name.lower() == type_str.lower() or
            map_type.name.lower().replace(" ", "").replace("-", "")
                == type_str.lower().replace(" ", "").replace("-", "")):
            return map_type

    short_matches = [mt for mt in MapArtType if mt.value.lower().startswith(type_str.lower())]

    if len(short_matches) == 1:
        return short_matches[0]

    return None


def get_map_palette(palette_str: str) -> MapArtPalette | None:
    """Returns the best effort mapping of the provided string to a MapArtPalette"""
    if palette_str.upper() in MapArtPalette:
        return MapArtPalette(palette_str.upper())

    for map_palette in MapArtPalette:
        if (map_palette.value.lower() == palette_str.lower() or
            map_palette.name.lower() == palette_str.lower() or
            map_palette.name.lower().replace(" ", "").replace("-", "")
                == palette_str.lower().replace(" ", "").replace("-", "")):
            return map_palette

    short_matches = [mp for mp in MapArtPalette if mp.value.lower().startswith(palette_str.lower())]

    if len(short_matches) == 1:
        return short_matches[0]

    return None


class SearchArgumentConverter(MixedArgsConverter):
    filter_flat_options: set[str] = {"-f", "-flat"}
    filter_carpet_only_options: set[str] = {"-c", "-co", "-carpet", "-carpetonly", "-carpet-only"}

    def __init__(self, default_min_size: int=0, default_order_by: order_by_arg= "date"):
        super().__init__()

        self.default_min_size = default_min_size
        self.default_order_by = default_order_by

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

            if parse_size_arg(arg, search_arguments):
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
                map_types = [get_map_type(t) for t in value]
                if exclude:  search_arguments.excluded_types.extend(map_types)
                else:        search_arguments.included_types.extend(map_types)
            elif "palette".startswith(key):
                map_palettes = [get_map_palette(p) for p in value]
                if exclude:  search_arguments.excluded_palettes.extend(map_palettes)
                else:        search_arguments.included_palettes.extend(map_palettes)
            elif "size".startswith(key):
                if exclude:
                    raise ValueError("cannot use exclusion for argument `size`")

                for size_arg in value:
                    parse_size_arg(size_arg, search_arguments)

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
