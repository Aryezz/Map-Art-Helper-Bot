import os
from json import loads


token = os.environ['TOKEN']  # Discord Bot Token
prefix = os.environ['PREFIX']  # Command Prefix
channel_blacklist = loads(os.environ["BLACKLIST"])  # List of channels IDs to ignore
# BLACKLIST environment variable format: '[111111111111111111, 222222222222222222]'
# replace channel ID placeholders
