import logging

import discord
from discord.ext import commands

logger = logging.getLogger("discord.mapart.exceptions")


class BlacklistedMapError(Exception):
    """Raised when a blacklisted map gets requested"""
    def __init__(self, map_id: int, user: discord.Member, message=None):
        self.map_id = map_id
        self.user = user
        self.error_message = message or f"Blacklisted map with id {self.map_id!s} was requested by user {self.user!s}"
        super().__init__(self.error_message)


class TransparentMapError(Exception):
    """Raised when a map is completly transparent"""
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
            case _:
                logger.error('Ignoring {} from message `{}`'.format(type(error).__name__, ctx.message.content))
                logger.error(error, exc_info=False, stack_info=True)


async def setup(client):
    await client.add_cog(CommandErrorHandler(client))
