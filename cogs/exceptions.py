import sys

import discord
from discord.ext import commands


class BlacklistedMapError(Exception):
    """Raised when a blacklisted map gets requested"""
    def __init__(self, map_id: int, user: discord.Member, message=None):
        self.map_id = map_id
        self.user = user
        self.message = message or f"Blacklisted map with id {self.map_id!s} was requested by user {self.user!s}"
        super().__init__(self.message)


class TransparentMapError(Exception):
    """Raised when a map is completly transparent"""
    def __init__(self, map_id: int):
        self.map_id = map_id
        super().__init__()


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return

        error = getattr(error, 'original', error)

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Missing Argument: " + str(error.param))
            return
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("Bad argument: " + str(error))
            return
        elif isinstance(error, commands.NSFWChannelRequired):
            await ctx.reply("This command can only be used in NSFW channels")
            return

        print('Ignoring {} in command {}:'.format(type(error).__name__, ctx.command), file=sys.stderr)


def setup(client):
    client.add_cog(CommandErrorHandler(client))
