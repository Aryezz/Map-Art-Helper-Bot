from discord.ext import commands


class BotStuffOnly(commands.CheckFailure):
    pass

def is_in_bot_stuff():
    bot_stuff_channel_id = 402917135225192458

    async def predicate(ctx):
        if ctx.channel.id != bot_stuff_channel_id:
            raise BotStuffOnly()
        return True

    return commands.check(predicate)
