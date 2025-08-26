import os
from json import loads


token = os.environ['TOKEN']  # Discord Bot Token
prefix = os.environ.get("PREFIX", "!!")  # Command Prefix

gemini_token = os.environ.get("GEMINI_API_KEY")  # API Key for Gemini API, Free tier is sufficient

map_artists_guild_id = os.environ.get('GUILD', 349201680023289867)
map_archive_channel_id = os.environ.get('ARCHIVE', 349277718954901514)

channel_blacklist = loads(os.environ["BLACKLIST"])  # List of channels IDs to ignore
# BLACKLIST environment variable format: '[111111111111111111, 222222222222222222]'
# replace channel ID placeholders
