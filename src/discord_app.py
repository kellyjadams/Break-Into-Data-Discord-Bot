import asyncio
import os
import logging
from datetime import (
    datetime, 
    timedelta, 
    timezone
)

import dotenv
import discord
from discord import app_commands
from discord.ext import tasks

from src.database import (
    get_user_goals,
    init_db,
    get_goal,
    ensure_user,
    get_category,
    new_submission,
)
from src.buttons import TrackSettingsView
from src.notifications.notifications import send_daily_notifications
from src.submissions.process_message import process_discord_message
from src.analytics.personal import get_personal_statistics
from src.analytics.leaderboard import get_weekly_leaderboard
from src.submissions.voice_submissions import process_voice_channel_activity
from src.ui.ml_30days import Challenge30DaysML


dotenv.load_dotenv()

DISCORD_TOKEN = os.environ['DISCORD_BOT_TOKEN']
SETTINGS_CHANNEL_ID = os.environ['DISCORD_SETTINGS_CHANNEL_ID']
GENERAL_CHANNEL_ID = os.environ['DISCORD_GENERAL_CHANNEL_ID']
DISCORD_SERVER_ID = os.environ['DISCORD_SERVER_ID']
SUBMISSION_CHANNEL_ID = os.environ['SUBMISSION_CHANNEL_ID']
# TODO: add this to config
CHALLENGE_30DAYS_ML_CHANNEL_ID = 1236400428724260996

intents = discord.Intents.all()
client = discord.Client(
    intents=intents,
)

logging.basicConfig(
    filename='bot.log',
    encoding='utf-8', 
    level=logging.DEBUG, 
    format='%(asctime)s:%(levelname)s:%(name)s:%(filename)s:line %(lineno)d: %(message)s'
)
logger = logging.getLogger(__name__)


@client.event
async def on_ready():
    """ Runs when the client becomes ready """
    logging.info('Logged in as %s', client.user)

    await tree.sync(guild=discord.Object(id=DISCORD_SERVER_ID))
    channel = await client.fetch_channel(SETTINGS_CHANNEL_ID)
    view = TrackSettingsView()
    logging.info('Checking for existing message with goal buttons.')

    msg_header = "**Pick your goal:**"
    async for message in channel.history(limit=2):
        if message.author == client.user and msg_header in message.content:
            # Found an existing message to update
            await message.edit(content=msg_header, view=view)
            logging.info('Updated existing message with goal buttons.')
            break
    else:
        # No existing message found
        await channel.send(msg_header, view=view)
        logging.info('No existing message. Sent new message.')
            
    channel = await client.fetch_channel(CHALLENGE_30DAYS_ML_CHANNEL_ID)
    logging.info('Checking for existing message with 30d ML buttons.')
    view_30days_ml = Challenge30DaysML()
    msg_header = "**30 Days ML Challenge**"
    async for message in channel.history(limit=2):
        if message.author == client.user and msg_header in message.content:
            # Found an existing message to update
            await message.edit(content=msg_header, view=view_30days_ml)
            logging.info('30 Days ML - Updated existing message.')
            break
    else:
        # No existing message found
        await channel.send(msg_header, view=view_30days_ml)
        logging.info('30 Days ML - No existing message. Sent new message.')
            
    await notify_by_timezone.start()

    await send_weekly_leaderboard.start()


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    await process_discord_message(message, SUBMISSION_CHANNEL_ID)


@client.event
async def on_voice_state_update(member, before, after):
    await process_voice_channel_activity(member, before, after)


@client.event
async def on_error(event, *args, **kwargs):
    logging.error(f'Unhandled error in {event}:', exc_info=True)


tree = app_commands.CommandTree(client)


@tree.command(
    name="submit",
    description="Submit your daily progress",
    guild=discord.Object(id=DISCORD_SERVER_ID),
)
async def submit_command(interaction, amount: int):
    logging.info(f'Processing submit command from {interaction.user}')
    # TODO: handle database errors

    await interaction.response.defer(thinking=True, ephemeral=True)

    #check - We do not use this rn (LLM instead) but needs to take a look.
    user, category = await asyncio.gather(
        ensure_user(interaction.user),
        get_category(interaction.channel.name)
    )

    if category is None:
        await interaction.followup.send(
            "You can't submit in this channel",
            ephemeral=True,
        )
        return

    goal = await get_goal(category.category_id, user.user_id)

    if goal is None:
        await interaction.followup.send(
            f'You don\'t have an active goal in category "{category.name}"',
            ephemeral=True,
        )
        return

    await new_submission(
        user_id=user.user_id,
        goal_id=goal.goal_id,
        proof_url=None,
        amount=amount,
    )

    logging.debug(f'Submit command processed for {interaction.user}')
    await interaction.followup.send("Your progress is saved!", ephemeral=True)


@tree.command(
    name="stats",
    description="Get personal stats for the last week",
    guild=discord.Object(id=DISCORD_SERVER_ID),
)
async def stats_command(interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)

    statistics = await get_personal_statistics(interaction.user.id)

    msg_parts = [
        f">>> **Personal stats for the last week **\n"
        f"**{interaction.user.global_name}**\n"
    ] + [
        f"**{category_name}**:\n"
        f"Submissions: {category_stats.submissions_number}\n"
        f"Active days: {category_stats.days_with_submissions}\n"
        for category_name, category_stats in statistics.by_category.items()
    ]

    msg = "\n".join(msg_parts)

    await interaction.followup.send(msg, ephemeral=False)


@tree.command(
        name="goals",
        description="To get your active goals",
        guild=discord.Object(id=DISCORD_SERVER_ID),
)
async def user_goals(interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)

    goals = await get_user_goals(interaction.user.id)
    if goals:
        msg_parts = [f"{goal.goal_description}: {goal.target} {goal.metric}, {goal.frequency} times a week" for goal in goals]
        goals_message = "\n".join(msg_parts)
        await interaction.followup.send(f">>> Here are your current goals:\n{goals_message}", ephemeral=False)
    else:
        await interaction.followup.send("You currently have no active goals.", ephemeral=False)


@tasks.loop(hours=1)
async def notify_by_timezone():
    await send_daily_notifications(client)
    

@tasks.loop(hours=24)
async def send_weekly_leaderboard():
    logging.info('Sending weekly leaderboard')
    channel = await client.fetch_channel(GENERAL_CHANNEL_ID)
    #Get last message in channel
    async for last_message in channel.history(limit=1):
        if last_message and last_message.author == client.user:
            if "Weekly leaderboard" in last_message.content:
                time_since_last_message = datetime.now(timezone.utc) - last_message.created_at
                if time_since_last_message < timedelta(hours=24):
                    # It's been less than 24 hours since the last leaderboard message
                    logging.info("Skipping sending leaderboard as it's been less than 24 hours.")
                    return
                
    leaderboards = await get_weekly_leaderboard()

    current_date = datetime.now().strftime("%d-%b-%Y")

    msg_parts = [f">>> **Weekly leaderboard: {current_date}**\n"]

    for category, leaderboard in leaderboards.items():
        if leaderboard:
            msg_parts.append(f"**{category}**")
            for user_id, submissions, days in leaderboard:
                username = (await client.fetch_user(user_id)).global_name
                msg_parts.append(f"{username}: {submissions} submissions, {days} active days")
            msg_parts.append("")

    msg = "\n".join(msg_parts)

    await channel.send(msg)
    logging.info('Successfully sent weekly leaderboard')


async def init():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("Please set the DATABASE_URL environment variable")

    await init_db(DATABASE_URL)
    
    discord.utils.setup_logging()
    return await client.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(init())
