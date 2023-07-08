import random
import re

from discord.ext import commands


class MemeCommands(commands.Cog, name="Memes"):
    """Pretty self explanatory, is it not?"""
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(self.bot, "yqe_message_count"):
            self.bot.yqe_message_count = 0

        self.yqe_user_id = 401027856316104706  # Yqe#5135
        self.golden_user_id = 394784819499761664  # Golden#9727

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.content.startswith(self.bot.command_prefix):
            return

        if message.author.id == self.yqe_user_id:
            self.bot.yqe_message_count += 1

        if message.author.id == self.golden_user_id:
            await message.add_reaction("🇦🇿")

        #if (
        #    re.search(r"\bFit(MC)?\b", message.content, flags=re.IGNORECASE) and
        #    message.channel.id not in self.bot.config.channel_blacklist
        #):
        #    await (await self.bot.get_context(message)).invoke(self.bot.get_command("fit"))

    @commands.command(hidden=True)
    async def yqe(self, ctx):
        """Most active discord user"""
        message = (
            f"Yqe has sent {self.bot.yqe_message_count!s} message{'s' if self.bot.yqe_message_count != 1 else ''} "
            f"since the bot was last restarted\n"
            "Yqe sends a lot of messages."
        )

        await ctx.send(message)

    @commands.command(hidden=True)
    async def tyrone(self, ctx):
        """It is known"""
        message = (
            "2b2t.org is the best Minecraft server. When you hear my name, and you will know who I am. Everyone knows who "
            "I am. My name is on the server. It is Popbob. And I'm always online because I have nothing better to do. "
            "Dear, I have autisms. Hausemaster, want to build a base together? Hausemaster. Hause. Hause. Hause... "
            "hause... hause... hause...."
        )

        await ctx.send(message)

    @commands.command(hidden=True)
    async def popbob(self, ctx):
        """trans icon"""
        message = "Popbob says trans rights :transgender_flag: :rainbow_flag:"

        await ctx.send(message)

    @commands.command(aliases=["hause"], hidden=True)
    async def hausemaster(self, ctx):
        """I wish him all the worst"""
        message = "Send Hatemail / Spam / Cupcake Recipes / etc. to support@2b2t.org"

        await ctx.send(message)

    @commands.command(aliases=["fitmc"], hidden=True)
    async def fit(self, ctx):
        """irrelevant"""
        message = f"FitMC? More Like {random.choice(['FatMC', 'BaldMC'])}! Gottem"

        await ctx.send(message)

    @commands.command(hidden=True)
    async def aa(self, ctx):
        """mood"""
        message = "aaaaaaaaaaaaaaaaa"

        await ctx.send(message)

    @commands.command(hidden=True)
    async def nodither(self, ctx):
        """no bitches?"""
        message = "https://cdn.discordapp.com/attachments/368137692099379209/947096808704860201/9469.png"

        await ctx.send(message)

    @commands.command(hidden=True)
    async def isthat(self, ctx):
        """a noobline?"""
        message = "https://cdn.discordapp.com/attachments/368137692099379209/947098578881482802/123abc_is_that_a_noob_line.png"

        await ctx.send(message)

    @commands.command(hidden=True)
    async def offtopic(self, ctx):
        """timeout for you"""
        message = "https://cdn.discordapp.com/attachments/368137692099379209/947104290298802216/unknown.png"

        await ctx.send(message)

    @commands.command(aliases=["no"], hidden=True)
    async def on(self, ctx):
        """god Haxified"""
        message = "https://cdn.discordapp.com/attachments/349277718954901514/598222928978640896/Capture.PNG"

        await ctx.send(message)


async def setup(client):
    await client.add_cog(MemeCommands(client))
