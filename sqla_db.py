import logging
import datetime
from typing import Iterable, Literal, Any

import sqlalchemy.ext.asyncio
from sqlalchemy import Column, Integer, String, ForeignKey, Table, select, Enum, desc, func, or_, DateTime, Boolean, \
    not_, and_, Select, asc
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship

from map_archive_entry import MapArtType, MapArtPalette, MapArtArchiveEntry

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
    maps = relationship("MapArtArchiveDBEntry", secondary=artist_mapart, back_populates="artists")

    def __str__(self):
        return self.name


class MapArtArchiveDBEntry(Base):
    __tablename__ = "map_art"
    map_id = Column(Integer, primary_key=True)
    width = Column(Integer)
    height = Column(Integer)
    type = Column(Enum(MapArtType), nullable=False)
    palette = Column(Enum(MapArtPalette), nullable=False)
    name = Column(String)
    artists = relationship("MapArtArtist", secondary=artist_mapart, back_populates="maps", lazy="selectin")
    notes = Column(String)
    image_url = Column(String)
    create_date = Column(DateTime)
    author_id = Column(Integer)
    message_id = Column(Integer)
    flagged = Column(Boolean)

    @property
    def create_date_utc(self):
        return self.create_date.replace(tzinfo=datetime.UTC)

    def as_entry(self):
        fixed_artists = []
        for artist in self.artists:
            fixed_artist = artist.name.replace("\r", "").replace("\n", "").strip()
            if fixed_artist:
                fixed_artists.append(fixed_artist)

        return MapArtArchiveEntry(
            map_id=self.map_id,
            width=self.width,
            height=self.height,
            map_type=self.type,
            palette=self.palette,
            name=self.name,
            artists=fixed_artists,
            notes=self.notes,
            image_url=self.image_url,
            create_date=self.create_date_utc,
            author_id=self.author_id,
            message_id=self.message_id,
            flagged=self.flagged,
        )


async def create_schema():
    async with Session.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class Session:
    engine = create_async_engine(f"sqlite+aiosqlite:///map_art.db")
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def __aenter__(self):
        self.session = Session.session_maker()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.commit()
        await self.session.close()

    def get_query_builder(self) -> 'MapArtQueryBuilder':
        return MapArtQueryBuilder(self.session)

    async def get_latest_create_date(self) -> datetime.datetime:
        query = select(func.max(MapArtArchiveDBEntry.create_date))
        date = (await self.session.execute(query)).scalar()
        return date.replace(tzinfo=datetime.UTC) if date is not None else datetime.datetime(2015, 1, 1, 0, 0, tzinfo=datetime.UTC)

    async def add_maps(self, maps: Iterable[MapArtArchiveEntry]):
        all_artist_names = set()

        for map_entry in maps:
            all_artist_names.update(map_entry.artists)

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
        for map_entry in maps:
            artist_entities = [artist_map[name] for name in map_entry.artists]

            if map_entry.map_id is not None:
                select_query = select(MapArtArchiveDBEntry).where(MapArtArchiveDBEntry.map_id == map_entry.map_id)
                db_entry = (await self.session.execute(select_query)).scalars().first()

                db_entry.width = map_entry.width
                db_entry.height = map_entry.height
                db_entry.type = map_entry.map_type
                db_entry.palette = map_entry.palette
                db_entry.name = map_entry.name
                db_entry.artists = artist_entities
                db_entry.notes = map_entry.notes
                db_entry.image_url = map_entry.image_url
                db_entry.create_date = map_entry.create_date
                db_entry.author_id = map_entry.author_id
                db_entry.message_id = map_entry.message_id
                db_entry.flagged = map_entry.flagged

                logger.info(f"updated map with id {map_entry.map_id}")
            else:
                maps_to_create.append(MapArtArchiveDBEntry(
                    width=map_entry.width,
                    height=map_entry.height,
                    type=map_entry.map_type,
                    palette=map_entry.palette,
                    name=map_entry.name,
                    artists=artist_entities,
                    notes=map_entry.notes,
                    image_url=map_entry.image_url,
                    create_date=map_entry.create_date,
                    author_id=map_entry.author_id,
                    message_id=map_entry.message_id,
                    flagged=map_entry.flagged
                ))

        if len(maps_to_create) > 0:
            self.session.add_all(maps_to_create)
            logger.info(f"added {len(new_artists)} artists and {len(maps_to_create)} maps")

        await self.session.flush()

    async def delete_maps(self, maps: Iterable[MapArtArchiveEntry]):
        map_ids_to_delete = [entry.map_id for entry in maps]

        db_entries = (await self.session.execute(select(MapArtArchiveDBEntry).where(MapArtArchiveDBEntry.map_id.in_(map_ids_to_delete)))).scalars().all()

        for db_entry in db_entries:
            await self.session.delete(db_entry)

    async def get_random_map(self) -> MapArtArchiveEntry:
        query = select(MapArtArchiveDBEntry).order_by(func.random()).limit(1)
        entry = (await self.session.execute(query)).scalars().first()
        return entry.as_entry() if entry is not None else None


class MapArtQueryBuilder:
    def __init__(self, session):
        self.session: sqlalchemy.ext.asyncio.AsyncSession = session
        self.query: Select[Any] = select(MapArtArchiveDBEntry)

    def order_by(self, field: Literal["size", "date"], reverse: bool = False):
        if field == "size":
            if not reverse:
                self.query = self.query.order_by(desc(MapArtArchiveDBEntry.width * MapArtArchiveDBEntry.height), asc(MapArtArchiveDBEntry.create_date))
            else:
                self.query = self.query.order_by(asc(MapArtArchiveDBEntry.width * MapArtArchiveDBEntry.height), desc(MapArtArchiveDBEntry.create_date))
        elif field == "date":
            if not reverse:
                self.query = self.query.order_by(asc(MapArtArchiveDBEntry.create_date))
            else:
                self.query = self.query.order_by(desc(MapArtArchiveDBEntry.create_date))

    def add_size_filter(self, min_size: int | None=None, max_size: int | None=None, exact_size: tuple[int, int] | None=None):
        if min_size is not None:
            self.query = self.query.where(MapArtArchiveDBEntry.width * MapArtArchiveDBEntry.height >= min_size)
        if max_size is not None:
            self.query = self.query.where(MapArtArchiveDBEntry.width * MapArtArchiveDBEntry.height <= max_size)
        if exact_size is not None:
            width, height = exact_size
            self.query = self.query.where(and_(MapArtArchiveDBEntry.width == width, MapArtArchiveDBEntry.height == height))

    def add_type_filter(self, include: list[MapArtArchiveEntry]=None, exclude: list[MapArtArchiveEntry]=None):
        if include is not None and len(include) >= 1:
            self.query = self.query.where(MapArtArchiveDBEntry.type.in_(include))
        if exclude is not None and len(exclude) >= 1:
            self.query = self.query.where(MapArtArchiveDBEntry.type.notin_(exclude))

    def add_palette_filter(self, include: list[MapArtPalette]=None, exclude: list[MapArtPalette]=None):
        if include is not None and len(include) >= 1:
            self.query = self.query.where(MapArtArchiveDBEntry.palette.in_(include))
        if exclude is not None and len(exclude) >= 1:
            self.query = self.query.where(MapArtArchiveDBEntry.palette.notin_(exclude))

    def add_artist_filter(self, include: list[str]=None, exclude: list[str]=None):
        if include is not None and len(include) >= 1:
            self.query = self.query.where(and_(*[MapArtArchiveDBEntry.artists.any(MapArtArtist.name.ilike(name)) for name in include]))
        if exclude is not None and len(exclude) >= 1:
            self.query = self.query.where(and_(*[not_(MapArtArchiveDBEntry.artists.any(MapArtArtist.name.ilike(name))) for name in exclude]))

    def add_duplicate_filter(self):
        self.query = self.query.where(MapArtArchiveDBEntry.message_id.in_(select(MapArtArchiveDBEntry.message_id).group_by(MapArtArchiveDBEntry.message_id).having(func.count() >= 2)))

    def add_search_filter(self, include=None, exclude=None):
        if include is not None and len(include) >= 1:
            for search_term in include:
                self.query = (self.query
                .join(MapArtArchiveDBEntry.artists)
                .where(or_(
                    MapArtArchiveDBEntry.name.contains(search_term),
                    MapArtArtist.name.ilike(search_term),
                    MapArtArchiveDBEntry.palette.ilike(search_term),
                    MapArtArchiveDBEntry.type.ilike(search_term),
                    MapArtArchiveDBEntry.message_id == search_term,
                    MapArtArchiveDBEntry.notes.ilike(search_term),
                )))

        if exclude is not None and len(exclude) >= 1:
            for search_term in exclude:
                self.query = (self.query
                .join(MapArtArchiveDBEntry.artists)
                .where(not_(or_(
                    MapArtArchiveDBEntry.name.contains(search_term),
                    MapArtArtist.name.ilike(search_term),
                    MapArtArchiveDBEntry.palette.ilike(search_term),
                    MapArtArchiveDBEntry.type.ilike(search_term),
                    MapArtArchiveDBEntry.message_id == search_term,
                    MapArtArchiveDBEntry.notes.ilike(search_term),
                ))))

    async def execute(self):
        db_entries = (await self.session.execute(self.query)).scalars().unique().all()
        return [entry.as_entry() for entry in db_entries]
