import asyncio
import csv
import enum

import sqlalchemy.ext.asyncio
from sqlalchemy import Column, Integer, String, ForeignKey, Table, select, Enum, desc
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


artist_mapart = Table(
    "artist_mapart",
    Base.metadata,
    Column("artist_id", Integer, ForeignKey("artist.artist_id")),
    Column("map_id", Integer, ForeignKey("map_art.map_id"))
)


class MapArtArtist(Base):
    __tablename__ = "artist"
    artist_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    maps = relationship("MapArtArchiveEntry", secondary=artist_mapart, back_populates="artists")

    @classmethod
    async def get_or_create_artist(cls, session, name: str):
        result = await session.execute(select(MapArtArtist).where(MapArtArtist.name == name))
        artist = result.scalar_one_or_none()
        if artist:
            return artist
        artist = MapArtArtist(name=name)
        session.add(artist)
        await session.flush()  # Ensures artist_id is populated
        return artist

    def __str__(self):
        return self.name


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


class MapArtArchiveEntry(Base):
    __tablename__ = "map_art"
    map_id = Column(Integer, primary_key=True)
    width = Column(Integer)
    height = Column(Integer)
    type = Column(Enum(MapArtType), nullable=False)
    palette = Column(Enum(MapArtPalette), nullable=False)
    name = Column(String)
    artists = relationship("MapArtArtist", secondary=artist_mapart, back_populates="maps", lazy="selectin")
    message_id = Column(Integer)

    @property
    def total_maps(self):
        return self.width * self.height

    @property
    def link(self):
        return "https://discord.com/channels/349201680023289867/349277718954901514/" + str(self.message_id)

    @property
    def artists_str(self):
        if len(self.artists) == 1:
            return self.artists[0].name

        artists_str = [a.name for a in self.artists]
        return ", ".join(artists_str[:-1]) + " and " + artists_str[-1]

    @property
    def line(self):
        size_info = f"{self.width} x {self.height} ({self.total_maps} maps)"
        extra_info = f"[{self.type}, {self.palette}] - [**{self.name}**]({self.link}) by **{self.artists_str}**"

        return size_info + " - " + extra_info


async def load_data(session: sqlalchemy.ext.asyncio.AsyncSession):
    type_mapping = {
        "flat": MapArtType.FLAT,
        "dual-layered": MapArtType.DUALLAYERED,
        "staircased": MapArtType.STAIRCASED,
        "semi-staircased": MapArtType.SEMISTAIRCASED
    }

    palette_mapping = {
        "full colour": MapArtPalette.FULLCOLOUR,
        "two-colour": MapArtPalette.TWOCOLOUR,
        "carpet only": MapArtPalette.CARPETONLY,
        "greyscale": MapArtPalette.GREYSCALE,
    }

    with open("map_arts.csv", "r", encoding="utf-8") as file:
        data = file.read()

    reader = csv.reader(
        filter(lambda line: not line.strip().startswith("#") and not line.strip() == "", data.split("\n")),
        delimiter=';', quotechar='"')

    maps = []

    for entry in reader:
        width = int(entry[0].strip())
        height = int(entry[1].strip())
        map_type = entry[2].strip()
        palette = entry[3].strip()
        name = entry[4].strip()
        artists = [a.strip() for a in entry[5].split(",")]
        message_id = int(entry[6].strip())

        artists_entities = []

        for artist in artists:
            a = await MapArtArtist.get_or_create_artist(session, artist)
            artists_entities.append(a)

        maps.append(MapArtArchiveEntry(
            width=width,
            height=height,
            type=type_mapping.get(map_type, MapArtType.UNKNOWN),
            palette=palette_mapping.get(palette, MapArtPalette.UNKNOWN),
            name=name,
            artists=artists_entities,
            message_id=message_id,
        ))

    session.add_all(maps)
    await session.commit()


async def get_session():
    engine = create_async_engine(f"sqlite+aiosqlite:///map_art.db")
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return async_session()


class MapArtQueryBuilder:
    def __init__(self, session):
        self.session: sqlalchemy.ext.asyncio.AsyncSession = session
        self.query = select(MapArtArchiveEntry).order_by(desc(MapArtArchiveEntry.width * MapArtArchiveEntry.height))

    def add_size_filter(self, min_size):
        self.query = self.query.where(MapArtArchiveEntry.width * MapArtArchiveEntry.height >= min_size)

    def add_type_filter(self, type: MapArtType):
        self.query = self.query.where(MapArtArchiveEntry.type == type)

    def add_palette_filter(self, palette: MapArtPalette):
        self.query = self.query.where(MapArtArchiveEntry.palette == palette)

    def add_artist_filter(self, artist: str):
        self.query = self.query.join(MapArtArchiveEntry.artists).where(MapArtArtist.name == artist)

    async def execute(self):
        return (await self.session.execute(self.query)).scalars().all()


async def main():
    engine = create_async_engine(f"sqlite+aiosqlite:///map_art.db")
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await load_data(async_session())

    print(select(MapArtArchiveEntry).where())

    async with async_session() as session:
        all_maps = (await session.execute(select(MapArtArchiveEntry))).scalars().all()

        print("\n".join(m.name for m in all_maps))




if __name__ == "__main__":
    asyncio.run(main())
