import json
import logging
from typing import List, Dict

import discord
from google import genai
from google.genai import types, errors
from pydantic import BaseModel

import config
from map_archive_entry import MapArtType, MapArtPalette

logger = logging.getLogger("discord.gemini")


class MapArtLLMOutput(BaseModel):
    width: int
    height: int
    map_type: MapArtType
    palette: MapArtPalette
    name: str
    artists: List[str]
    notes: str
    message_id: int


def serialize_message(message: discord.Message) -> Dict:
    return {
        "author": message.author.display_name,
        "content": message.clean_content,
        "message_id": message.id,
        "attachments": [a.url.split("?")[0].split("/")[-1] for a in message.attachments],
    }


async def process_messages(messages: List[discord.Message]) -> List[MapArtLLMOutput]:
    client = genai.Client(
        api_key=config.gemini_token,
    )

    message_dicts = [serialize_message(message) for message in messages]

    model = "gemini-2.5-flash-lite"
    contents = (
        "Process the following serialized Discord messages to extract info. "
        "The messages describe Minecraft map arts and contain some structured properties. "
        "If there are references to original artists, you can ignore those, and just return the builders/printers/mappers as the artists. "
        "If no size is provided, you can assume 1x1. For all sizes you can assume width comes before height. "
        "The output should contain one entry for every message with one or more attachments. "
        "Messages without attachments cannot ever represent an output entry, except if there are image links in the message content, which do not get recognized as attachments. "
        "Messages without attachments or image links might add relevant information for following messages. "
        "For the message_id field, always use the message ID of the message containing the image (link or attachment). Never return a message_id which is not contained in the input. "
        "If there are special notable additional infos in the message, add them to notes. "
        "If no name is not provided, try to extract a suitable name from the attachment url, if the url contains no suitable name, use the name \"unknown\". Never use the file extension in the name.\n\n"
    ) + json.dumps(message_dicts)
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=list[MapArtLLMOutput]
    )

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        logger.info(f"processed {len(messages)} message(s), used {response.usage_metadata.total_token_count} tokens")

        response_parsed = response.parsed

        if response_parsed is not None:
            logger.info(response.text)

            return response_parsed
        else:
            logger.error("response was empty, returning empty list")
            return []
    except errors.APIError as e:
        logger.error(f"Error Code {e.code} while processing")
        logger.error(e.message)
        return []
