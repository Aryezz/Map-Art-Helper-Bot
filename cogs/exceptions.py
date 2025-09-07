import logging
import traceback

import discord
from discord.ext import commands

from cogs import checks


logger = logging.getLogger("discord.mapart.exceptions")


class BlacklistedMapError(Exception):
    """Raised when a blacklisted map gets requested"""
    def __init__(self, map_id: int, user: discord.Member, message=None):
        self.map_id = map_id
        self.user = user
        self.error_message = message or f"Blacklisted map with id {self.map_id!s} was requested by user {self.user!s}"
        super().__init__(self.error_message)


class TransparentMapError(Exception):
    """Raised when a map is completely transparent"""
    def __init__(self, map_id: int):
        self.map_id = map_id
        super().__init__()


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        error = getattr(error, 'original', error)

        match error:
            case commands.CommandNotFound():
                pass  # prevent log spam from typos, etc.
            case commands.MissingRequiredArgument():
                await ctx.reply("Missing Argument: " + str(error.param))
            case commands.BadArgument():
                await ctx.reply("Bad argument: " + str(error))
            case commands.NSFWChannelRequired():
                await ctx.reply("This command can only be used in NSFW channels")
            case commands.BadUnionArgument():
                await ctx.reply("Arguments could not be parsed, check format")
            case commands.DisabledCommand():
                await ctx.reply("This command is currently disabled")
            case checks.BotChannelsOnly():
                await ctx.reply("This command only works in bot channels (channels starting with `bot-`)")
            case commands.CheckFailure():
                await ctx.reply("A check for this command failed")
            case _:
                tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
                message = f"An error occurred:\n```py\n{tb}\n```"
                await ctx.send(message)
                logger.error(f"Ignoring error:\n{tb}")


async def setup(client):
    await client.add_cog(CommandErrorHandler(client))
