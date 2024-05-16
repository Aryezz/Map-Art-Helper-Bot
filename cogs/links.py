from discord.ext import commands


class LinkCommands(commands.Cog, name="Links"):
    """Commands linking to external websites or past discussions"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["mif", "format"])
    async def wiki(self, ctx):
        """Minecraft Map Item Format on the Minecraft Wiki"""
        message = "https://minecraft.wiki/Map_item_format"

        await ctx.send(message)

    @commands.command(aliases=["mac"])
    async def mapartcraft(self, ctx):
        """Map Art Generator made by rebane2001#3716"""
        message = (
            "https://rebane2001.com/mapartcraft/\n"
            "made with :heart: by rebane2001#3716"
        )

        await ctx.send(message)

    @commands.command(aliases=["maw", "wall"])
    async def mapartwall(self, ctx):
        """Map Art Wall made by rebane2001#3716"""
        message = (
            "https://rebane2001.com/mapartwall/\n"
            "made with :heart: by rebane2001#3716"
        )

        await ctx.send(message)

    @commands.command()
    async def bookart(self, ctx):
        """Like Map Art but in books"""
        message = (
            "Check out the discussion here:\n"
            "https://discord.com/channels/349201680023289867/368137692099379209/930486853918933032 "
            "(scroll down for more screenshots)"
        )

        await ctx.send(message)

    @commands.command()
    async def moire(self, ctx):
        """It's like acid"""
        message = (
            "Check out the discussion here:\n"
            "https://discord.com/channels/349201680023289867/349480851915931653/919933674177306646"
        )

        await ctx.send(message)

    @commands.command(aliases=["prio", "queue", "prioq", "prioqueue"])
    async def priorityqueue(self, ctx):
        """The official 2b2t shop"""
        message = "https://shop.2b2t.org (don't do it though)"

        await ctx.send(message)

    @commands.command()
    async def invite(self, ctx):
        """Discord invite for this server"""
        message = "https://discord.gg/r7Tuerq"

        await ctx.send(message)

    @commands.command()
    async def printer(self, ctx):
        """Link to THCFree's litematica printer with 2b2t Grim bypass"""
        message = (
            "https://github.com/THCFree/litematica-printer/releases/latest\n"
            "also read the [README](https://github.com/THCFree/litematica-printer)\n"
            "**NOTE: USE MODS AT YOUR OWN RISK, ANY MOD COULD BE A RAT!!!**"
        )

        await ctx.send(message)


async def setup(client):
    await client.add_cog(LinkCommands(client))
