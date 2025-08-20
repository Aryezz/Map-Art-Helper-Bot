from dataclasses import dataclass
from typing import Tuple, List


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
        size_info = f"{self.size[0]} x {self.size[1]} ({self.total_maps} maps)"
        extra_info = f"[{self.type}, {self.palette}] - [**{self.name}**]({self.link}) by **{self.artists_str}**"

        return size_info + " - " + extra_info