import random
from datetime import datetime

from discord.ext import commands
import humanize


class MemeCommands(commands.Cog, name="Memes"):
    """Pretty self-explanatory, is it not?"""

    yqe_user_id = 401027856316104706  # @yqe
    golden_user_id = 394784819499761664  # @heyitsgolden
    tutulalasisi_user_id = 598539347838369812  # @tutulalasisi
    tutulalasisi_command_answers = [
        "Wtf is bro yapping about?",
        "I ain't adding more commands, my man",
        "That's not a real command (and never will be!)",
        "You need professional `!!help`",
        "\"{command_yap}\", this is how you sound",
    ]

    def __init__(self, bot):
        self.bot = bot
        if not hasattr(self.bot, "yqe_message_count"):
            self.bot.yqe_message_count = 0

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.content.startswith(self.bot.command_prefix):
            return

        if message.author.id == MemeCommands.yqe_user_id:
            self.bot.yqe_message_count += 1

        if message.author.id == MemeCommands.golden_user_id:
            await message.add_reaction("🇦🇿")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            if ctx.author.id == MemeCommands.tutulalasisi_user_id:
                text = ctx.message.content
                command_yap = "".join(a + b for (a, b) in zip(text[::2].lower(), text[1::2].upper())) + text[-1] if len(text) % 2 == 1 else ""
                await ctx.reply(random.choice(self.tutulalasisi_command_answers).format(command_yap=command_yap))

    @commands.command(hidden=True)
    async def smallest(self, ctx):
        await ctx.send(f"{ctx.author.mention} pp :microscope:")

    @commands.command(hidden=True)
    async def updog(self, ctx):
        await ctx.send(f"not much, how about you?")

    @commands.command(hidden=True)
    async def yqe(self, ctx):
        """Most active discord user"""
        delta = self.bot.started - datetime.now()
        delta_f = humanize.precisedelta(delta, minimum_unit="hours", suppress=["years", "months"], format="%d")
        message = (
            f"Yqe has sent {self.bot.yqe_message_count!s} message{'s' if self.bot.yqe_message_count != 1 else ''} "
            f"since the bot was last restarted {delta_f} ago.\n"
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
