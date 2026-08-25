import dataclasses
from datetime import datetime, timezone, timedelta
import hashlib
from collections import defaultdict

import discord
from discord.ext import commands, tasks

import config


def _normalize(text: str) -> str:
    return text.strip().casefold()


def _hash(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


@dataclasses.dataclass
class MessageRecord:
    first_seen: datetime
    messages: list[discord.Message]

    def get_channel_ids(self) -> set[int]:
        return {message.channel.id for message in self.messages}


class Moderation(commands.Cog, name="Moderation"):
    """Server moderation tools"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # cache[user_id][hash]: MessageRecord
        self.cache: dict[int, dict[str, MessageRecord]] = defaultdict(dict)
        self.bot_log_channel: discord.TextChannel = self.bot.get_channel(config.bot_log_channel_id)

    async def cog_load(self) -> None:
        self.filter_cache.start()

    def cog_unload(self) -> None:
        self.filter_cache.cancel()

    @tasks.loop(seconds=10)
    async def filter_cache(self):
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=30)
        for user_id, records in list(self.cache.items()):
            filtered_records = {message_hash: record for message_hash, record in records.items() if record.first_seen >= cutoff}

            if not filtered_records:
                del self.cache[user_id]
            else:
                self.cache[user_id] = filtered_records

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if "staff" in [role.name for role in message.author.roles]:
            return
        if message.content.startswith(self.bot.command_prefix):
            return
        if not message.guild:
            return
        if not message.content or not message.content.strip():
            return

        message_hash = _hash(message.content)

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=30)

        if record := self.cache[message.author.id].get(message_hash):
            record.messages.append(message)
            message_count = len(record.get_channel_ids())
            if record.first_seen >= cutoff and message_count >= 3:
                # temporary action: alert staff, don't kick user or delete any messages
                # TODO: add kick and message deletion when we're sure that there are no false positives
                message = f"detected spammer {message.author.mention} in {message_count} channels <@&349427930234880009>"
                await self.bot_log_channel.send(message)
        else:
            self.cache[message.author.id][message_hash] = MessageRecord(message.created_at, [message])


async def setup(client):
    await client.add_cog(Moderation(client))
