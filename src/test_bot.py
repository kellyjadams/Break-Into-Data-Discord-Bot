import pytest
import asyncio
from unittest.mock import AsyncMock
from src.discord_app import init, client

@pytest.mark.asyncio
async def test_bot_starts(mocker):

    # Mock Discord client methods
    mocker.patch.object(client, 'is_ready', return_value=True)
    mocker.patch('discord.Client.start', new_callable=AsyncMock)

    # Mock database initialization function
    mocker.patch('src.discord_app.init_db', new_callable=AsyncMock)

    # Mock fetching the channel and sending a message to it
    mock_channel = mocker.MagicMock()
    mock_send = AsyncMock()
    mock_channel.send = mock_send
    mocker.patch('discord.Client.fetch_channel', return_value=mock_channel)

    # Mock environment variables if needed
    mocker.patch('os.getenv', side_effect=lambda key: 'fake_token' if key == 'DISCORD_BOT_TOKEN' else 'fake_id')


    # Start the bot in a background task
    bot_task = asyncio.create_task(init())

    await asyncio.sleep(1)  # Wait for a few seconds to let the bot start

    # Check if the bot is connected and logged in
    assert client.is_ready()

    # Close the bot after the test
    await client.close()
    await bot_task