import asyncio
import os
import logging
from datetime import (
    datetime, 
    timezone,
)

from dotenv import load_dotenv

from src.models import TimeZoneEnum
from src.database import (
    get_users_to_notify, 
    update_user_timezone_shift,
    get_users_without_timezone_shift,
)


logger = logging.getLogger(__name__)

load_dotenv()

DISCORD_SERVER_ID = os.environ['DISCORD_SERVER_ID']
NOTIFICATION_CHANNEL_ID = os.environ['NOTIFICATION_CHANNEL_ID']


async def notify_users_in_timezone(notification_channel, utc_offset):
    now = datetime.now(timezone.utc)
    
    if now.hour == (24 + utc_offset) % 24:
        users_to_notify = await get_users_to_notify(utc_offset)
        
        batch_size = 5
        for idx in range(0, len(users_to_notify), batch_size):
            batch = users_to_notify[idx:idx + batch_size]
            msg = '\n'.join([
                f'Hey <{username}>! It\'s time to submit your daily goal!\n'
                f'You have submitted {submissions_count} goals so far. :tada:\n'
                for username, submissions_count in batch
            ])
        
            await notification_channel.send(msg)
    

async def _set_missing_timezone_shifts(client):
    logger.info('Setting missing timezone shifts')
    guild = await client.fetch_guild(DISCORD_SERVER_ID)
    
    users = await get_users_without_timezone_shift()
    
    for user in users[:100]:
        user_id = user[0]
        member = guild.get_member(str(user_id))
        if member is None:
            continue
        role = ...
        breakpoint()
        await update_user_timezone_shift(user_id, role)
        await asyncio.sleep(2)


async def send_daily_notifications(client):
    await _set_missing_timezone_shifts(client)
    
    logger.info('Sending notifications')
    channel = await client.fetch_channel(NOTIFICATION_CHANNEL_ID)

    for time_zone in TimeZoneEnum:
        await notify_users_in_timezone(channel, time_zone.value)
