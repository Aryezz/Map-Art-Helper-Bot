from discord.ext import commands


class BotChannelsOnly(commands.CheckFailure):
    pass

def is_in_bot_channel():
    async def predicate(ctx):
        if not ctx.channel.name.startswith("bot-"):
            raise BotChannelsOnly()
        return True

    return commands.check(predicate)
