import os

from dotenv import load_dotenv
import groq
from groq import AsyncGroq

load_dotenv()

groq_client = AsyncGroq(
    api_key=os.environ["GROQ_API_KEY"]
)


async def get_groq_response(question: str) -> str:
    try:
        response = await groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful assistant for the Break Into Data Discord server."
                },
                {
                    "role": "user", 
                    "content": question
                }
            ],
            temperature=1.0,
        )
        return response.choices[0].message.content
    except groq.APIConnectionError as e:
        print("The server could not be reached")
        print(e.__cause__)
        return "I'm sorry, I couldn't connect to the Groq server. Please try again later."
    except groq.RateLimitError as e:
        print("A 429 status code was received; we should back off a bit.")
        return "I'm sorry, we've hit the rate limit. Please try again in a moment."
    except groq.APIStatusError as e:
        print("Another non-200-range status code was received")
        print(e.status_code)
        print(e.response)
        return "I'm sorry, there was an error with the AI service. Please try again later."
    except Exception as e:
        print(f"Error in getting AI response: {e}")
        return "I'm sorry, I couldn't generate a response at the moment."
