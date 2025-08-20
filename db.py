import csv

import aiosqlite

from cogs.map_art import BigMapArt

type_mapping = {
    "flat": "FLAT",
    "dual-layered": "DUAL LAYERED",
    "staircased": "STAIRCASED",
    "semi-staircased": "SEMI STAIRCASED"
}

palette_mapping = {
    "full colour": "FULL COLOUR",
    "two-colour": "TWO COLOUR",
    "carpet only": "CARPET ONLY",
    "greyscale": "GREYSCALE"
}


async def create_schema(db: aiosqlite.Connection):
    await db.execute(r"""
                     CREATE TABLE IF NOT EXISTS Map_Type
                     (
                         id   INTEGER PRIMARY KEY AUTOINCREMENT,
                         name TEXT UNIQUE
                     );
                     """)

    await db.execute(r"""
                     INSERT OR IGNORE INTO Map_Type (name)
                     VALUES ('STAIRCASED'),
                            ('SEMI STAIRCASED'),
                            ('FLAT'),
                            ('DUAL LAYERED'),
                            ('UNKNOWN');
                     """)

    await db.execute(r"""
                     CREATE TABLE IF NOT EXISTS Palette
                     (
                         id   INTEGER PRIMARY KEY AUTOINCREMENT,
                         name TEXT UNIQUE
                     );
                     """)

    await db.execute(r"""
                     INSERT OR IGNORE INTO Palette (name)
                     VALUES ('FULL COLOUR'),
                            ('TWO COLOUR'),
                            ('GREYSCALE'),
                            ('CARPET ONLY'),
                            ('UNKNOWN');
                     """)

    await db.execute(r"""
                     CREATE TABLE IF NOT EXISTS Artist
                     (
                         id   INTEGER PRIMARY KEY AUTOINCREMENT,
                         name TEXT UNIQUE
                     );
                     """)

    await db.execute(r"""
                     CREATE TABLE IF NOT EXISTS Artist_Map_Art
                     (
                         artist_id INTEGER,
                         map_id    INTEGER,
                         PRIMARY KEY (artist_id, map_id),
                         FOREIGN KEY (artist_id) REFERENCES Map_Type (id),
                         FOREIGN KEY (map_id) REFERENCES Palette (id)
                     );
                     """)

    await db.execute(r"""
                     CREATE TABLE IF NOT EXISTS Map_Art
                     (
                         id         INTEGER PRIMARY KEY AUTOINCREMENT,
                         width      INTEGER,
                         height     INTEGER,
                         type       INTEGER,
                         palette    INTEGER,
                         name       TEXT,
                         message_id INTEGER,
                         FOREIGN KEY (type) REFERENCES Map_Type (id),
                         FOREIGN KEY (palette) REFERENCES Palette (id)
                     );
                     """)

    await db.commit()


async def add_map(db: aiosqlite.Connection, m: BigMapArt):
    for artist in m.artists:
        await db.execute(r"""
                         INSERT OR IGNORE INTO Artist (name)
                         VALUES (?);
                         """, (artist,))

    cursor = await db.execute(r"SELECT id FROM Map_Type WHERE name = ?", (type_mapping.get(m.type, "UNKNOWN"),))
    type_id = (await cursor.fetchone())[0]

    cursor = await db.execute(r"SELECT id FROM Palette WHERE name = ?", (palette_mapping.get(m.palette, "UNKNOWN"),))
    palette_id = (await cursor.fetchone())[0]

    await db.execute(r"""
                     INSERT INTO Map_Art (width, height, type, palette, name, message_id)
                     VALUES (?, ?, ?, ?, ?, ?);
                     """,
                     (
                         m.size[0],
                         m.size[1],
                         type_id,
                         palette_id,
                         m.name,
                         m.message_id,
                     )
                     )

    cursor = await db.execute(r"SELECT id FROM Map_Art WHERE id = (SELECT max(id) FROM Map_Art);")
    map_id = (await cursor.fetchone())[0]

    for artist in m.artists:
        cursor = await db.execute(r"SELECT id FROM Artist WHERE name = ?", (artist,))
        artist_id = (await cursor.fetchone())[0]
        await db.execute(r"INSERT OR IGNORE INTO Artist_Map_Art (artist_id, map_id) VALUES "
                         r"(?, ?)", (artist_id, map_id))

    await db.commit()


async def load_data(db: aiosqlite.Connection):
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
        maps.append(BigMapArt((width, height), map_type, palette, name, artists, message_id))

    for m in maps:
        await add_map(db, m)


async def get_big_maps(db: aiosqlite.Connection):
    cursor = await db.execute(r"""
                              SELECT width, height, MT.name, P.name, MA.name, GROUP_CONCAT(A.name, ';'), message_id
                              FROM main.Map_Art MA
                                       JOIN main.Palette P ON MA.palette = P.id
                                       JOIN main.Map_Type MT ON MA.type = MT.id
                                       JOIN main.Artist_Map_Art AMA ON MA.id = AMA.map_id
                                       JOIN main.Artist A ON AMA.artist_id = A.id
                              WHERE MA.width * MA.height >= 32
                              GROUP BY MA.id;
                              """)

    maps = await cursor.fetchall()

    return [BigMapArt((m[0], m[1]), m[2], m[3], m[4], m[5].split(";"), m[6]) for m in maps]
