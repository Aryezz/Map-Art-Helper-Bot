import json
import logging
import os
from typing import List

import discord
from google import genai
from google.genai import types, errors
from google.genai.errors import APIError

logger = logging.getLogger("discord.gemini")


def serialize_message(message: discord.Message):
    msg_dict = {
        "author": message.author.global_name,
        "author_id": message.author.id,
        "content": message.content,
        "message_id": message.id,
        "attachments": [a.url for a in message.attachments]
    }

    if isinstance(message.author, discord.Member):
        msg_dict["author_nick"] = message.author.nick

    mentions = []

    for mention in message.mentions:
        if isinstance(mention, discord.Member):
            mentions.append({"name": mention.global_name, "nick": mention.nick, "id": mention.id})

    msg_dict["mentions"] = mentions

    return msg_dict


async def process_messages(messages: List[discord.Message]):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    message_dicts = [serialize_message(message) for message in messages]

    model = "gemini-2.5-flash-lite"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=(
                        "Process the following serialized Discord messages to extract info. "
                        "The messages describe Minecraft map arts and contain some structured properties. "
                        "If the message contains user mentions, use the mentions to evaluate which users are mentioned where. "
                        "If there are references to original artists or people preprocessing the image, you can ignore those, and just return the builders/printers/mappers as the artists. "
                        "If no size is provided, you can assume 1x1. For all sizes you can assume width comes before height. "
                        "If no name is not provided, try to extract a suitable name from the attachment url, if the url contains no suitable name, use the name \"unknown\". "
                        "In rare cases, multiple consecutive messages relate to a single map art entry, in those cases, use the message id of the message containing an image attachment.\n\n"
                    ) + json.dumps(message_dicts)
                ),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=0,
        ),
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["map_arts"],
            properties={
                "map_arts": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        required=["width", "height", "type", "palette", "name", "artists", "message_id"],
                        properties={
                            "width": genai.types.Schema(
                                type=genai.types.Type.INTEGER,
                            ),
                            "height": genai.types.Schema(
                                type=genai.types.Type.INTEGER,
                            ),
                            "type": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                enum=["FLAT", "DUALLAYERED", "STAIRCASED", "SEMISTAIRCASED", "UNKNOWN"],
                            ),
                            "palette": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                enum=["FULLCOLOUR", "TWOCOLOUR", "CARPETONLY", "GREYSCALE", "UNKNOWN"],
                            ),
                            "name": genai.types.Schema(
                                type=genai.types.Type.STRING,
                            ),
                            "artists": genai.types.Schema(
                                type=genai.types.Type.ARRAY,
                                items=genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                ),
                            ),
                            "message_id": genai.types.Schema(
                                type=genai.types.Type.INTEGER,
                            ),
                        },
                    ),
                ),
            },
        ),
    )

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        logger.info(f"processed {len(messages)} message(s), used {response.usage_metadata.total_token_count} tokens")

        map_list = response.parsed["map_arts"]
        return map_list
    except errors.APIError as e:
        logger.error(f"Error Code {e.code} while processing")
        logger.error(e.message)
