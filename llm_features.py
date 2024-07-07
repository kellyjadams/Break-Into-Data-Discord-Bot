import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

openai_client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)


async def get_ai_response(question: str) -> str:
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-2024-05-13",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful assistant for the Break Into Data discord server."
                },
                {
                    "role": "user", 
                    "content": question
                }
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in getting AI response: {e}")
        return "I'm sorry, I couldn't generate a response at the moment."
