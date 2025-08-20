from datetime import datetime
import logging

from discord import Intents
from discord.ext import commands
from discord.ext.commands import DefaultHelpCommand

import config

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(
    intents=intents,
    command_prefix=config.prefix,
    case_insensitive=True,
    help_command=DefaultHelpCommand(width=250)
)

logger = logging.getLogger("discord.mapart.init")

@bot.event
async def on_ready():
    bot.config = config
    bot.started = datetime.now()
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logger.info('Guilds:')
    logger.info("\n".join(["* " + g.name async for g in bot.fetch_guilds()]))

    cogs = ["cogs.memes", "cogs.help", "cogs.links", "cogs.misc", "cogs.map_archive", "cogs.exceptions"]

    for cog in cogs:
        await bot.load_extension(cog)
        logger.info(f"loaded cog {cog}")


@bot.check
async def ignore_dms(ctx):
    return ctx.guild is not None


@bot.check
async def delete_archive_commands(ctx):
    return ctx.message.channel.id not in config.channel_blacklist


if __name__ == "__main__":
    bot.run(config.token)
