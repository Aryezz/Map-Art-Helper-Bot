import json
import os

import discord
import aiohttp

api_key=os.environ.get("GEMINI_API_KEY")
model_id="gemini-2.5-flash-lite"
generate_content_api="generateContent"


gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:{generate_content_api}?key={api_key}"


def serialize_message(msg: discord.Message):
    msg_dict = {
        "author": msg.author.name,
        "author_nick": msg.author.nick,
        "author_id": msg.author.id,
        "content": msg.content,
        "id": msg.id,  # TODO: it would probably make more sense to add the message id manually afterwards instead of having the LLM do it
        "mentions": [{"name": m.name, "nick": m.nick, "id": m.id} for m in msg.mentions],
    }

    return msg_dict

async def process_message(message):
    request = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Process the following serialized Discord message to extract info. The message describes a Minecraft map art and contains some structured properties. If the message contains user mentions, use the mentions to evaluate which users are mentioned where.\n\n" + json.dumps(message)
                    },
                ]
            },
        ],
        "generationConfig": {
            "thinkingConfig": {
                "thinkingBudget": 0,
            },
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "map_arts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "width": {
                                    "type": "integer"
                                },
                                "height": {
                                    "type": "integer"
                                },
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "flat",
                                        "dual-layered",
                                        "staircased",
                                        "semi-staircased",
                                        "unknown"
                                    ]
                                },
                                "palette": {
                                    "type": "string",
                                    "enum": [
                                        "full colour",
                                        "two-colour",
                                        "carpet only",
                                        "greyscale",
                                        "unknown"
                                    ]
                                },
                                "name": {
                                    "type": "string"
                                },
                                "artists": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "message_id": {
                                    "type": "integer"
                                }
                            },
                            "required": [
                                "width",
                                "height",
                                "type",
                                "palette",
                                "name",
                                "artists",
                                "message_id"
                            ],
                            "propertyOrdering": [
                                "width",
                                "height",
                                "type",
                                "palette",
                                "name",
                                "artists",
                                "message_id"
                            ]
                        }
                    }
                },
                "required": [
                    "map_arts"
                ],
                "propertyOrdering": [
                    "map_arts"
                ]
            },
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(gemini_url, json=request) as response:
            response_json = await response.json()
            map_list = json.loads(bytes(response_json["candidates"][0]["content"]["parts"][0]["text"], "utf-8").decode("unicode_escape"))["map_arts"]

            return map_list
