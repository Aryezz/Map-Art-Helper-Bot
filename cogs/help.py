from discord.ext import commands


class HelpCommands(commands.Cog, name="Help"):
    """Commands answering common questions about map art"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def noobline(self, ctx):
        """What nooblines are and how to fix them"""
        message = (
            "Nooblines (the top line of the maps being in a lighter shade than the rest of the map - "
            "see screenshot for an example) can be fixed by placing a line of blocks north of the actual "
            "map (mapartcraft actually already generates a line of stone blocks for this reason, you "
            "just have to align the map correctly)\n"
            "https://cdn.discordapp.com/attachments/349277718954901514/619582190103166986/unknown.png"
        )

        await ctx.send(message)

    @commands.command(aliases=["stair", "3d", "staircased", "shades"])
    async def staircase(self, ctx):
        """How staircased maps produce different shades of colours"""
        message = (
            "Every block has one of three shades depending on the height of the highest block directly on its north. "
            "If the highest block directly on its north is lower, the light shade is displayed, if it's on the same "
            "height the middle shade is displayed (this is the colour a block would have on a flat map) and if it's "
            "higher the dark shade is displayed.\n"
            "This is also the reason why nooblines exist, use !!noobline for more info.\n"
            "The screenshot below shows the three shades of white a staircased map can produce.\n"
            "https://cdn.discordapp.com/attachments/349439171196354561/980070154027282543/unknown.png"
        )

        await ctx.send(message)

    @commands.command(aliases=["artist"])
    async def role(self, ctx):
        """How to get the artist role on here"""
        message = (
            "To get the artist role, you have to post a screenshot of your map in #screenshots and ping staff.\n"
            "After you have the artists role you can post your map in the archive\n"
            "Note that your map has to be built on 2b2t and your screenshot should include the tablist as proof."
        )

        await ctx.send(message)

    @commands.command()
    async def animated(self, ctx):
        """Different concepts of animated maps"""
        message = (
            "There are a couple different concepts for animated maps:\n"
            "\"truly animated\" maps that work with water and lava as seen in this video: <https://youtu.be/_O_dAKlsysM>\n"
            "maps that show different frames in combination with a mod that spins the player in the correct direction"
            "as seen in these videos: <https://youtu.be/xUzbpMONaG4> and <https://youtu.be/8vDiZPdGB-8>\n"
            "and maps that are animated by spinning them as seen here: <https://youtu.be/iyCy_AvTKkg>\n"
            "there is also a concept with a pig and speedhacks allthough none of these maps have ever been built on 2b2t: "
            "https://discord.com/channels/349201680023289867/349201680023289869/483866707753172992\n\n"
            "here are relevant posts in the archive:\n"
            "https://discord.com/channels/349201680023289867/349277718954901514/609829167500099604\n"
            "https://discord.com/channels/349201680023289867/349277718954901514/609829257958523002\n"
            "https://discord.com/channels/349201680023289867/349277718954901514/609829370567327760\n"
            "https://discord.com/channels/349201680023289867/349277718954901514/635967350243590157\n"
            "https://discord.com/channels/349201680023289867/349277718954901514/708588867854401577\n"
            "https://discord.com/channels/349201680023289867/349277718954901514/929513076741509130"
        )

        await ctx.send(message)

    @commands.command(aliases=["reset"])
    async def mapreset(self, ctx):
        """Explanation of map resets"""
        message = (
            "Since map IDs in Minecraft are stored as signed shorts (16 bits) maps can be overwritten by causing an "
            "integer overflow. To do this someone just has to spam enough maps (filling out the 32.768 actual IDs and "
            "the 32.767 negative IDs - which will all be blank - to arrive back at map number 0. From there on every "
            "new map will overwrite an old one with the same ID)\n\n"
            "Maps were first disabled by \"The 4th Reich\" after the 11/11 dupe (they filled out all map IDs which "
            "meant any newly created map would have a negative ID and be blank, a reupload of the video can be found here: "
            "<https://youtu.be/znN9w2-Ojeo>). Later Kinorana would complete the reset by filling out all negative IDs and "
            "overwriting all existing maps with his own (a map of Idolm@sters Chihaya): "
            "<https://twitter.com/barrendome/status/835888276808478720>\n"
            "A bunch of the original map art that existed before the first reset can be found here: "
            "<https://i.imgur.com/RcN0xiq.jpg>\n"
            "Maps still get regularly reset to this day.\n"
        )

        await ctx.send(message)

    @commands.command()
    async def void(self, ctx):
        """Void on maps"""
        message = "Void has the same colour on a map as stone, it will not make the map transparent."

        await ctx.send(message)

    @commands.command()
    async def nether(self, ctx):
        """About maps in the nether"""
        message = (
            "Maps do not work in the nether, see the example screenshot:\n"
            "https://minecraft.wiki/images/Nethermap.png"
        )

        await ctx.send(message)

    @commands.command(aliases=["dither"])
    async def dithering(self, ctx):
        """Explanation of dithering"""
        message = (
            "Dithering is an intentional use of noise to reduce the error of compression (such as the reduction of "
            "available colours when creating map art). It is used to prevent colour banding (see the example below, "
            "where the left side is undithered and the right side is dithered using the Floyd-Steinberg algorithm)\n"
            "https://cdn.discordapp.com/attachments/349201680023289869/944598422722330654/unknown.png"
        )

        await ctx.send(message)

    @commands.command()
    async def text(self, ctx):
        """Tips for text on maps"""
        message = (
            "When your map has text - especially small text - you should manually paint it in before building the map "
            "to prevent it from looking blurry. Below are two examples, the first of which is barely readable in places "
            "unlike the second one, which despite having way smaller text is perfectly readable.\n"
            "https://cdn.discordapp.com/attachments/349201680023289869/898636796764766239/unknown-3.png\n"
            "https://cdn.discordapp.com/attachments/349277718954901514/561550842969456689/unknown.png"
        )

        await ctx.send(message)

    @commands.command()
    async def align(self, ctx):
        """Info on the alignment of maps"""
        message = (
            "Minecraft Maps are aligned on a grid that lines up with the chunk grid. Unzoomed maps cover 8 x 8 chunks. "
            "The simplest way to find the borders of your map is to just create a map and walk to a corner, but you "
            "might want to avoid this on anarchy servers to prevent people terrain exploiting. You can also create a "
            "singleplayer world with cheats enabled and teleport to the coordinates of your base and figure out the grid "
            "offline without risk of leaking terrain.\n"
            "A third option is to calculate the coordinates of top left chunk of a map with the following formula: "
            "`floor((coordinate + 4) / 8) * 8 - 4` (use this on both X and Z of your chunk coordinates)\n"
            "If you still have questions, get them cleared up before you start building your map, because there is no way "
            "to fix a misaligned map!"
        )

        await ctx.send(message)

    @commands.command()
    async def seed(self, ctx):
        """2b2t's map seed(s)"""
        message = (
            "**2b2t map seeds**\n"
            "overworld: -4172144997902289642\n"
            "nether/end: 1434823964849314312"
        )

        await ctx.send(message)

    @commands.command()
    async def water(self, ctx):
        """Water on maps"""
        message = (
            "Check out the info here:\n"
            "https://discord.com/channels/349201680023289867/349201680023289869/934067758327537695"
        )

        await ctx.send(message)

    @commands.command()
    async def glass(self, ctx):
        """Glass on maps"""
        message = "Glass does not affect maps in any way shape or form, it might as well be air."

        await ctx.send(message)

    @commands.command()
    async def lightning(self, ctx):
        """Info about lightning strikes"""
        message = (
            "Lightning strikes can burn holes in your map, to prevent this add a layer of glass on top or never load "
            "the chunks after completion."
        )

        await ctx.send(message)

    @commands.command(name="1.13", aliases=["113"])
    async def _113(self, ctx):
        """Graphic explaining differences between 1.12 and 1.13"""
        message = "https://cdn.discordapp.com/attachments/565597105629036557/664880778857152515/lsSQR11.png"

        await ctx.send(message)

    @commands.command()
    async def bedrock(self, ctx):
        """Map Art on Bedrock and Pocket edition"""
        message = (
            "The #mapart-guide channel in the Map Artists of 2b2e discord guild has full guide on how to create map "
            "art on bedrock and pocket edition. https://discord.gg/Y3gpgGR9yD"
        )

        await ctx.send(message)


async def setup(client):
    await client.add_cog(HelpCommands(client))
