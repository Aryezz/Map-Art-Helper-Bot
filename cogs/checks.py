from discord.ext import commands


class BotStuffOnly(commands.CheckFailure):
    pass

def is_in_bot_stuff():
    bot_stuff_channel_id = [402917135225192458, 1295775975082168370]

    async def predicate(ctx):
        if ctx.channel.id not in bot_stuff_channel_id:
            raise BotStuffOnly()
        return True

    return commands.check(predicate)
