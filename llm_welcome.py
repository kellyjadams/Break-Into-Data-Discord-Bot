from email import message
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.submissions import process_message

load_dotenv()

openai_client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)


PROMPT = """Write a 1 sentence witty data-related welcome message for {username} who just joined the \"Break Into Data\" discord server. 
Also provide a title seperated by a newline. Do not output anything else.
"""


def process_welcome_message(message: str) -> str:
    splits = message.split("\n\n")
    message = splits[1].strip()

    if 'title:' in splits[0].lower():
        title = splits[0].split('title:')[1].strip()
    else:
        title = splits[0].strip()
    
    return title, message


async def generate_welcome_message(username: str) -> str:
    prompt = PROMPT.format(
        username=username,
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4o-2024-05-13",
        messages=[{
            "role": "system",
            "content": prompt,
        }],
        temperature=1.0,
        tool_choice=None
    )

    message = response.choices[0].message.content

    return process_welcome_message(message)
