import dataclasses
import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks

import config

_logger = logging.getLogger("discord.moderation")


def _normalize(text: str) -> str:
    return text.strip().casefold()


def _hash_message(message: discord.Message) -> str:
    hash_string = f"{len(message.attachments)};{message.content}"
    return hashlib.sha256(_normalize(hash_string).encode("utf-8")).hexdigest()


_kick_message = (
        "You have been kicked from Map Artists of 2b2t <:mcmap:349454913526562816> for suspected spam.\n\n" +
        "If you were not posting there yourself moments ago, your Discord account has likely been compromised and is "
        "being actively used by spammers as you read this. You should immediately change your password to lock them out "
        "(seriously, stop reading and do that right now), and try to find and block through what means your information "
        "was stolen. Otherwise they may still be able to get into your account again despite the password change.\n"
        "The most common ways people get compromised are fake login forms on phishing sites, malware, or bots you "
        "unknowingly authorized to post on your behalf. Phishing sites usually can't get back in after a password "
        "change, and you can deauthorize some bots in Discord's settings. Identifying malware is beyond the scope of "
        "this message, as it can be difficult to track down and is not always detected by antivirus. However, if this "
        "happens again after a password change and deauthorizing bots, you know it was caused by something you used, or "
        "that ran, in the time since.\n\n"
        "When you have properly secured your account, you can rejoin."
)


def _boolean_emoji(boolean: bool):
    return ":white_check_mark:" if boolean else ":x:"


@dataclasses.dataclass
class MessageRecord:
    first_seen: datetime
    author: discord.Member
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
            filtered_records = {message_hash: record for message_hash, record in records.items() if
                                record.first_seen >= cutoff}

            if not filtered_records:
                del self.cache[user_id]
            else:
                self.cache[user_id] = filtered_records

    @staticmethod
    async def _remove_spam(record: MessageRecord) -> tuple[bool, bool, int]:
        sent_kick_message = False
        try:
            await record.author.send(_kick_message)
            sent_kick_message = True
        except discord.Forbidden:
            _logger.error("No permission to send kick message")
        except discord.HTTPException:
            _logger.error("HTTP exception while sending kick message")

        kicked_member = False
        try:
            await record.author.kick(reason=f"spam detected")
            kicked_member = True
        except discord.Forbidden:
            _logger.error("No permission to kick member")
        except discord.HTTPException:
            _logger.error("HTTP exception while kicking member")

        deleted_count = 0
        for message in record.messages:
            try:
                await message.delete()
                deleted_count += 1
            except discord.Forbidden:
                _logger.error("No permission to delete message")
            except discord.NotFound:
                _logger.error("Message to delete could not be found")
            except discord.HTTPException:
                _logger.error("HTTP exception while deleting message")

        return sent_kick_message, kicked_member, deleted_count

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

        message_hash = _hash_message(message)

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=30)

        if record := self.cache[message.author.id].get(message_hash):
            record.messages.append(message)
            message_count = len(record.get_channel_ids())
            if record.first_seen >= cutoff and message_count >= 3:
                msg_sent, kicked, delete_count = await self._remove_spam(record)

                message = (f"detected spammer {message.author.mention}\n" +
                           f"kick message sent: {_boolean_emoji(msg_sent)}\n" +
                           f"member kicked: {_boolean_emoji(kicked)}\n" +
                           f"messages deleted: {delete_count}/{len(record.messages)}")
                await self.bot_log_channel.send(message)
        else:
            self.cache[message.author.id][message_hash] = MessageRecord(message.created_at, message.author, [message])


async def setup(client):
    await client.add_cog(Moderation(client))
