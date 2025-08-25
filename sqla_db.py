import csv
import enum
import logging

from sqlalchemy import Column, Integer, String, ForeignKey, Table, select, Enum, desc, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship


logger = logging.getLogger("discord.db")


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
        """Returns a grammatically correct, comma-separated string of artist names."""
        names = [artist.name for artist in self.artists]
        if len(names) == 0:
            return ""
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{', '.join(names[:-1])}, and {names[-1]}"

    @property
    def line(self):
        size_info = f"{self.width} x {self.height} ({self.total_maps} maps)"
        extra_info = f"[{self.type}, {self.palette}] - [**{self.name}**]({self.link}) by **{self.artists_str}**"

        return size_info + " - " + extra_info


class Session:
    async def __aenter__(self):
        engine = create_async_engine(f"sqlite+aiosqlite:///map_art.db")
        self.session = async_sessionmaker(engine, expire_on_commit=False)()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.commit()
        await self.session.close()

    def get_query_builder(self):
        return self.MapArtQueryBuilder(self.session)

    async def get_latest_message_id(self):
        return (await self.session.execute(select(func.max(MapArtArchiveEntry.message_id)))).scalar()

    async def add_maps(self, maps):
        type_mapping = {
            "flat": MapArtType.FLAT,
            "dual-layered": MapArtType.DUALLAYERED,
            "staircased": MapArtType.STAIRCASED,
            "semi-staircased": MapArtType.SEMISTAIRCASED,
            "unknown": MapArtType.UNKNOWN,
        }

        palette_mapping = {
            "full colour": MapArtPalette.FULLCOLOUR,
            "two-colour": MapArtPalette.TWOCOLOUR,
            "carpet only": MapArtPalette.CARPETONLY,
            "greyscale": MapArtPalette.GREYSCALE,
            "unknown": MapArtPalette.UNKNOWN,
        }

        all_artist_names = set()

        for map in maps:
            all_artist_names.update(map["artists"])

        existing_artists_query = await self.session.execute(
            select(MapArtArtist).where(MapArtArtist.name.in_(all_artist_names)))
        existing_artists = {artist.name: artist for artist in existing_artists_query.scalars()}

        new_artist_names = all_artist_names - set(existing_artists.keys())
        new_artists = [MapArtArtist(name=name) for name in new_artist_names]
        self.session.add_all(new_artists)
        await self.session.flush()  # Populate IDs for new artists

        artist_map = existing_artists
        for artist in new_artists:
            artist_map[artist.name] = artist

        maps_to_create = []
        for parsed_entry in maps:
            artist_entities = [artist_map[name] for name in parsed_entry["artists"]]
            maps_to_create.append(MapArtArchiveEntry(
                width=parsed_entry["width"],
                height=parsed_entry["height"],
                type=type_mapping.get(parsed_entry["type"], MapArtType.UNKNOWN),
                palette=palette_mapping.get(parsed_entry["palette"], MapArtPalette.UNKNOWN),
                name=parsed_entry["name"],
                artists=artist_entities,
                message_id=parsed_entry["message_id"],
            ))

        self.session.add_all(maps_to_create)

        logger.info(f"added {len(new_artists)} artists and {len(maps_to_create)} maps")

        await self.session.flush()

    async def load_data(self):
        with open("map_arts.csv", "r", encoding="utf-8") as file:
            data = file.read()

        reader = csv.reader(
            filter(lambda line: not line.strip().startswith("#") and not line.strip() == "", data.split("\n")),
            delimiter=';', quotechar='"')

        parsed_entries = []
        for entry in reader:
            width = int(entry[0].strip())
            height = int(entry[1].strip())
            map_type = entry[2].strip()
            palette = entry[3].strip()
            name = entry[4].strip()
            artists = [a.strip() for a in entry[5].split(",")]
            message_id = int(entry[6].strip())

            parsed_entries.append({
                "width": width,
                "height": height,
                "type": map_type,
                "palette": palette,
                "name": name,
                "artists": artists,
                "message_id": message_id,
            })

        await self.add_maps(parsed_entries)

    class MapArtQueryBuilder:
        def __init__(self, session):
            self.session = session
            self.query = select(MapArtArchiveEntry).order_by(desc(MapArtArchiveEntry.width * MapArtArchiveEntry.height))

        def add_size_filter(self, min_size):
            self.query = self.query.where(MapArtArchiveEntry.width * MapArtArchiveEntry.height >= min_size)

        def add_type_filter(self, type: MapArtType):
            self.query = self.query.where(MapArtArchiveEntry.type == type)

        def add_palette_filter(self, palette: MapArtPalette):
            self.query = self.query.where(MapArtArchiveEntry.palette == palette)

        def add_artist_filter(self, artist: str):
            self.query = self.query.join(MapArtArchiveEntry.artists).where(MapArtArtist.name.ilike(artist))

        async def execute(self):
            return (await self.session.execute(self.query)).scalars().all()
