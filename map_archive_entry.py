import enum
from dataclasses import dataclass

from datetime import datetime
from typing import List, Optional

import config


class MapArtType(enum.Enum):
    FLAT = "flat"
    DUALLAYERED = "dual-layered"
    STAIRCASED = "staircased"
    SEMISTAIRCASED = "semi-staircased"
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value


class MapArtPalette(enum.Enum):
    FULLCOLOUR = "full colour"
    TWOCOLOUR = "two-colour"
    CARPETONLY = "carpet only"
    GREYSCALE = "greyscale"
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value


@dataclass
class MapArtArchiveEntry:
    width: int
    height: int
    map_type: MapArtType
    palette: MapArtPalette
    name: str
    artists: List[str]
    notes: str
    image_url: str
    create_date: datetime
    author_id: int
    message_id: int
    map_id: Optional[int] = None
    flagged: bool = False

    @property
    def total_maps(self):
        return self.width * self.height

    @property
    def link(self):
        return f"https://discord.com/channels/{config.map_artists_guild_id}/{config.map_archive_channel_id}/{self.message_id}"

    @property
    def artists_str(self):
        """Returns a grammatically correct, comma-separated string of artist names."""
        names = [artist for artist in self.artists]
        if len(names) == 0:
            return ""
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{', '.join(names[:-1])}, and {names[-1]}"

    @property
    def line(self):
        size_info = f"{self.width} x {self.height} ({self.total_maps} {"map" if self.total_maps == 1 else "maps"})"
        extra_info = f"[{self.map_type}, {self.palette}] - [**{self.name}**]({self.link}) by **{self.artists_str}**"

        return size_info + " - " + extra_info