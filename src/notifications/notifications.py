import asyncio
import os
import logging
from datetime import (
    datetime, 
    timezone,
)
import discord

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
        logger.info(f'Notifying users in timezone {utc_offset}')
        users_to_notify = await get_users_to_notify(utc_offset)
        logger.info(f'Users to notify: {users_to_notify}')
        
        batch_size = 5
        for idx in range(0, len(users_to_notify), batch_size):
            batch = users_to_notify[idx:idx + batch_size]
            msg = '\n'.join([
                f'Hey <{username}>! It\'s time to submit your daily goal!\n'
                f'You have submitted {submissions_count} goals so far. :tada:\n'
                for username, submissions_count in batch
            ])

            await notification_channel.send(msg)


def _get_tz_shift_for_member(member: discord.Member):
    for role in member.roles:
        role_name = role.name.replace(' ', '_')
        try:
            return TimeZoneEnum[role_name].value
        except KeyError:
            continue
    return None


async def _set_missing_timezone_shifts(client):
    logger.info('Setting missing timezone shifts')
    # For some reason fetching guild doesn't return members
    guild = [
        guild for guild in client.guilds if guild.id == int(DISCORD_SERVER_ID)
    ][0]
    
    # returns list of tuples (user_id, timezone_shift)
    users = await get_users_without_timezone_shift()
    users_by_id = {user[0]: user for user in users}
    
    # For some reason fetching members returns None
    #   so we have to iterate over all the guild members..
    for member in guild.members:
        if member.bot:
            continue
        user = users_by_id.get(member.id)
        if user is None:
            print(f'User {member.name} not found in the database')
            continue
        user_id, old_tz_shift = user
        
        if old_tz_shift is not None:
            print(f'User {member.name} already has a timezone shift')
            continue
        
        tz_shift = _get_tz_shift_for_member(member)
        if tz_shift is None:
            print(f'User {member.name} has no timezone shift role')
            continue
        
        await update_user_timezone_shift(user_id, tz_shift)


async def send_daily_notifications(client):
    await _set_missing_timezone_shifts(client)
    
    channel = await client.fetch_channel(NOTIFICATION_CHANNEL_ID)

    for time_zone in TimeZoneEnum:
        await notify_users_in_timezone(channel, time_zone.value)
