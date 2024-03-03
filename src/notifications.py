from src.database import select_raw 
import os
import discord
from discord.ext import commands, tasks
import asyncio
import pytz
from datetime import datetime, timedelta

# Assuming you have a Discord bot setup
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())


async def get_users_not_submitted(time_zone_name: str):
    # Placeholder for your database query function
    # This should return a list of usernames who haven't submitted
    time_zone_name = f"%{time_zone_name}%"
    print(time_zone_name)
    usernames = await select_raw("""
        SELECT DISTINCT u.username
        FROM users u
        JOIN goals g ON u.user_id = g.user_id
        LEFT JOIN submissions s ON u.user_id = s.user_id
        WHERE s.submission_id IS NULL
        AND u.user_roles like :time_zone_name
    """,time_zone_name=time_zone_name)

    return usernames

async def notify_users_in_timezone(timezone_name, utc_offset):
    current_utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)
    target_timezone = pytz.timezone(utc_offset)
    local_time = current_utc_time.astimezone(target_timezone)
    print(f'local time is {local_time}for {timezone_name}')

    if local_time.hour == 17:  # Check if it's 12 PM
        users_to_notify = await get_users_not_submitted(timezone_name)
        print(f'users to notify{users_to_notify}')
        notification_channel = os.environ['NOTIFICATION_CHANNEL_ID']

        if users_to_notify and notification_channel:
            await notification_channel.send(
                f"It's 12 PM in {timezone_name}. YO WHERE IS THE SUBMISSION MAN for: " + ", ".join([f"@{username}" for username in users_to_notify])
            )















      










def count_submissions(submissions):
    count_dictionary = {}
    for submission in submissions:
        if submission.username not in count_dictionary:
            count_dictionary[submission.username] = 1
        else:
            count_dictionary[submission.username] += 1 
    return count_dictionary


def find_users_who_did_not_submit(client, users_who_submitted_recently, count_dictionary):
     users_who_submitted = {}
     for user in users_who_submitted_recently:
         users_who_submitted[user.username] = True 

     users_to_notify = {}

     for user in client.get_all_members():
        username = str(user)
        if username not in users_who_submitted:
            users_to_notify[username] = True 
        if username not in count_dictionary:
            count_dictionary[username] = 0
     return users_to_notify
    












