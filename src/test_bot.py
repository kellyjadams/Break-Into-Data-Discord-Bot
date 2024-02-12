import pytest
import asyncio
from src.discord_app import init, client 

@pytest.mark.asyncio
async def test_bot_starts():

    # Start the bot in a background task
    bot_task = asyncio.create_task(init())

    await asyncio.sleep(5)  # Wait for a few seconds to let the bot start

    # Check if the bot is connected and logged in
    assert client.is_ready()

    # Close the bot after the test
    await client.close()
    await bot_task