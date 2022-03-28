import asyncio

import aiohttp
from discord.ext import commands

import config


bot = commands.Bot(command_prefix=config.prefix, case_insensitive=True)


@bot.event
async def on_ready():
    bot.session = aiohttp.ClientSession()
    bot.config = config
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('Guilds:')
    print("\n".join("* " + g.name for g in (await bot.fetch_guilds().flatten())))

    cogs = ["cogs.memes", "cogs.help", "cogs.links", "cogs.misc", "cogs.exceptions"]

    for cog in cogs:
        bot.load_extension(cog)

    print('------')


@bot.check
async def ignore_dms(ctx):
    return ctx.guild is not None


@bot.check
async def delete_archive_commands(ctx):
    return ctx.message.channel.id in config.channel_blacklist


bot.run(config.token)
