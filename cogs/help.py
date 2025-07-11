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
            "an even more advanced map art redstone machine supporting 16 colours is shown here: <https://youtu.be/E9AI1V0dzVA>\n"
            "and another redstone machine: <https://youtu.be/UxER9BCrHUM>"
            "maps that show different frames in combination with a mod that spins the player in the correct direction"
            "as seen in these videos: <https://youtu.be/xUzbpMONaG4> and <https://youtu.be/8vDiZPdGB-8>\n"
            "and maps that are animated by spinning them as seen here: <https://youtu.be/iyCy_AvTKkg>\n"
            "there is also a concept with a pig and speed hacks or boats on ice although none of these maps have ever "
            "been built on 2b2t: https://discord.com/channels/349201680023289867/349201680023289869/483866707753172992 "
            "<https://www.youtube.com/shorts/iup9fyI15Y0?feature=share>\n\n"
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
            "Up until Minecraft 1.13 map IDs were stored as signed shorts (16 bits). This meant that the map ID "
            "counter would overflow when after reaching 32'767 and reset to -32'768. If all of the negative map IDs "
            "were again used up and the map ID counter got back to zero, new maps would start overwriting existing"
            "IDs.\n"
            "Maps were first disabled by \"The 4th Reich\" after the 11/11 dupe (they filled out all map IDs which "
            "meant any newly created map would have a negative ID and be blank. A reupload of the video can be found "
            "here: <https://youtu.be/znN9w2-Ojeo>). Later Kinorana would complete the reset by filling out all "
            "negative IDs and overwriting all existing maps with his one of their own (a map of Idolm@sters Chihaya): "
            "<https://twitter.com/barrendome/status/835888276808478720>\n"
            "A bunch of the original map art that existed before the first reset can be found here: "
            "<https://i.imgur.com/RcN0xiq.jpg>\n"
            "Maps were reset many times after that, but since 1.13 map IDs are stored as signed ints (32 bits) instead "
            "of shorts, and negative map IDs behave the same as positive ones, meaning there are a total of "
            "4'294'967'296 different possible map IDs. This means maps can no longer be disabled and a complete reset "
            "is all but impossible."
        )

        await ctx.send(message)

    @commands.command()
    async def void(self, ctx):
        """Void on maps"""
        message = (
            "Watch this video for information about using the void to create transparent maps: "
            "https://youtu.be/UZ6pniCQMEQ"
        )

        await ctx.send(message)

    @commands.command()
    async def baritone(self, ctx):
        """Info on how to use baritone to build map art"""
        message = (
            "**Tutorial on how to build map art using Baritone** (by JeeJ_LEL and Radagon)\n"
            "> To build map art with baritone, you have to load your schematic with litematica and then enter "
            "`#litematica build` to start.\n"
            "> Note that it is not 100% autonomous and can get stuck, so look after it. `#pause` and `#resume` "
            "are your friends.\n"
            "> It can't restock automatically from chests or shulkers, but it can move items in your inventory with "
            "the right setting : `#allowinventory true` . Turn it off once you're done to avoid affecting regular "
            "gameplay (the pickaxe stuck on slot 1).\n"
            "> Baritone cannot deal with mobs. It's best to prevent mob spawning beforehand, but they can also be "
            "dealt with kill aura with a knockback sword and thorns armor.\n"
            "> The command `#buildIgnoreProperties powered,power,type` prevents baritone from getting stuck on "
            "pressure plates, and from caring whether slabs are top or bottom.\n"
            "> \n"
            "> It works better if you first put a platform below to help it (eg for staircased). If your schematic "
            "includes one, the setting `#buildskipblocks block1,block2,block3` (list all non-platform materials) "
            "allows you to build the platform before the rest.\n"
            "> It struggles with non-full blocks such as carpets, especially on staircased maps where it can get stuck "
            "whenever it needs to jump on a carpet. It is preferable to only use full blocks when building staircased "
            "maps with baritone.\n"
            "> The setting `#mapArtMode true` makes it only care about the top block in each column, which is useful "
            "for staircased maps. On the contrary, the *buildInLayers* setting should be disabled.\n"
            "Baritone: <https://github.com/cabaletta/baritone>\n"
            "**NOTE: USE MODS AT YOUR OWN RISK, ANY MOD COULD BE A RAT!!!**\n"
            "If you need to convert your .NBT file output from Mapartcraft into a .LITEMATIC, follow the guide bellow. "
            "Baritone only reads .litematic files.\n"
            "https://media.discordapp.net/attachments/565597105629036557/1201107698574438500/Capture_decran_2024-01-28_103628.png"
        )

        await ctx.send(message)

    @commands.command(aliases=["act"])
    async def photoshop(self, ctx):
        """Info about dithering in photoshop"""
        message = (
            "# Dithering in Photoshop\n"
            "Follow the tutorial in this video: https://youtu.be/8VRuDEfFa2Y\n"
            "Instead of the NES colour palette, choose one of the following ACT colour profiles:\n"
            "* staircase palette: https://cdn.discordapp.com/attachments/565597105629036557/1209546913259589752/staircase_new.ACT?ex=65e75158&is=65d4dc58&hm=65f55ac19ecb76045cc3a94215a3a71f7a17b31477eb127e8c368f9d439e5678\n"
            "* flat palette: https://cdn.discordapp.com/attachments/565597105629036557/1209546913771421746/flat_new.ACT?ex=65e75158&is=65d4dc58&hm=3c03f21ccd0a0f09b7906472e9e5cc11e2b8ebb99a3f41f2911d8b6e538a3341"
        )

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

    @commands.command(aliases=["res"])
    async def resolution(self, ctx):
        """Tradeoffs concerning resolution"""
        message = (
            "# Resolution & Detail\n"
            "Each Minecraft map covers a 128x128 block area. Using multiple maps enhances resolution and allows for "
            "finer details.\n"
            "\n"
            "**Complexity & Color Constraints**\n"
            "Single-map artworks have fewer pixels, limiting detail. Larger map art (e.g., 2x2 or 3x3 maps) provides "
            "higher detail but demands more time and resources.\n"
            "Maps with very high resolution may show aliasing artifacts, see `!!moire` for more info.\n"
            "\n"
            "**Example**\n"
            "The first image is Angel's Mirror by KevinKC2014, measuring 21x12. In this version, the mouth, ears, "
            "scars, and hands are clearly visible.\n"
            "The second image is a 3x2 version of Angel's Mirror, where the mouth, ears, scars, and hands are not "
            "visible, and the image appears noticeably pixelated.\n"
            "https://media.discordapp.net/attachments/402917135225192458/1349948902681477242/Angels_Mirror.png\n"
            "https://media.discordapp.net/attachments/402917135225192458/1349948903201443840/Untitled.png"
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
            "**2b2t map seeds [Only accurate up to 1.12.2 terrain]**\n"
            "overworld: -4172144997902289642\n"
            "nether/end: 1434823964849314312"
        )

        await ctx.send(message)

    @commands.command()
    async def water(self, ctx):
        """Water on maps"""
        message = (
            "Water is not affected by the height of the block north of it (like other blocks are). "
            "Instead the different shades can be produced using different water depths: "
            "https://media.discordapp.net/attachments/349480851915931653/1167752798818009088/2023-10-28_02.11.07.png"
        )

        await ctx.send(message)

    @commands.command()
    async def glass(self, ctx):
        """Glass on maps"""
        message = "Glass does not affect maps in any way shape or form, it might as well be air, except for `!!void`."

        await ctx.send(message)

    @commands.command()
    async def lightning(self, ctx):
        """Info about lightning strikes"""
        message = (
            "Lightning strikes can burn holes in your map, to prevent this, add lightning rods on the 4 corners of the "
            "map (after locking it), add layer of glass on top or never load the chunks after completion."
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
