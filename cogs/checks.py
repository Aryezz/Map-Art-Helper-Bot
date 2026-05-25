from discord.ext import commands
from discord.ext.commands import has_role, is_owner


class BotChannelsOnly(commands.CheckFailure):
    pass

def is_in_bot_channel():
    async def predicate(ctx):
        if not ctx.channel.name.startswith("bot-"):
            raise BotChannelsOnly()
        return True

    return commands.check(predicate)


def is_staff_or_owner():
    return commands.check_any(has_role("staff"), is_owner())
