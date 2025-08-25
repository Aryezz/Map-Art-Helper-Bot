import json
import os

import discord
from google import genai
from google.genai import types


def serialize_message(msg: discord.Message):
    msg_dict = {
        "author": msg.author.name,
        "author_nick": msg.author.nick,
        "author_id": msg.author.id,
        "content": msg.content,
        "id": msg.id,
        # TODO: it would probably make more sense to add the message id manually afterwards instead of having the LLM do it
        "mentions": [{"name": m.name, "nick": m.nick, "id": m.id} for m in msg.mentions],
    }

    return msg_dict


async def process_message(message):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash-lite"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text="Process the following serialized Discord message to extract info. The message describes a Minecraft map art and contains some structured properties. If the message contains user mentions, use the mentions to evaluate which users are mentioned where.\n\n" + json.dumps(
                        message)),
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

    response = await client.aio.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    map_list = response.parsed["map_arts"]
    return map_list
