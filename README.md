# Map Art Helper Bot

This is a discord bot for the *Map Artists of 2b2t* guild.
If you aren't already a member, you can join here: [Discord Invite](http://discord.gg/r7Tuerq)

The bot was made to prevent important information / interesting discussions from getting lost in the endless depths of
channel logs, and to provide some convenience features related to map art on 2b2t. If you have any suggestions for
improvements or new commands, please message me on Discord.


## Configuration
The following environment variables can be configured

* `TOKEN` Discord bot token
* `PREFIX` Command Prefix (default: `!!`)
* `GEMINI_API_KEY` API key for Google Gemini (Free tier is sufficient)
* `GUILD` Discord Guild ID (default: `349201680023289867`, the Map Artists of 2b2t Guild)
* `ARCHIVE` Discord channel ID (default: `349277718954901514`, the map-archive channel in the guild)
* `BLACKLIST` List of Discord channel IDs where commands are ignored (default: `[]`)
* `BOT_LOG` Discord channel ID (default: `1409872078508920872`, the bot-log channel in the guild)
