import asyncio
import os
from dataclasses import dataclass
from datetime import datetime

import dotenv
import discord
from discord import app_commands
from discord.ext import tasks

from src.database import (
    get_category_by_name,
    get_category_for_voice,
    init_db, 
    get_goal,
    new_goal, 
    ensure_user,
    get_category, 
    new_submission,
)

from src.analytics.leaderboard import get_weekly_leaderboard
from src.analytics.personal import get_personal_statistics

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SETTINGS_CHANNEL_ID = os.getenv('DISCORD_SETTINGS_CHANNEL_ID')
GENERAL_CHANNEL_ID = os.getenv('DISCORD_GENERAL_CHANNEL_ID')
DISCORD_SERVER_ID = os.getenv('DISCORD_SERVER_ID')

client = discord.Client(
    intents=discord.Intents.all(),
)


@dataclass
class Track:
    name: str
    default_tracking_value: str
    default_daily_target: int


TRACKS = {
    track.name: track for track in [
        Track(name="Fitness", default_tracking_value="Minutes / Number of pushups", default_daily_target=30),
        Track(name="Leetcode", default_tracking_value="Minutes spent / Number of problems solved", default_daily_target=3),
        Track(name="Studying", default_tracking_value="Minutes spent", default_daily_target=60),
        Track(name="Other", default_tracking_value="Smiles", default_daily_target=10),
    ]
}


class TrackSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__()

        for track in TRACKS.values():
            self.add_button(track)

    def add_button(self, track: Track):
        btn = discord.ui.Button(label=track.name, style=discord.ButtonStyle.secondary, custom_id=track.name)
        self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return False
        track = TRACKS.get(interaction.data['custom_id'])
        if not track:
            interaction.response.send_message("Something went wrong, please try again", ephemeral=True)
            return False
        
        modal = TrackSettingsModal(track)
        await interaction.response.send_modal(modal)

        return True


class TrackSettingsModal(discord.ui.Modal):
    def __init__(self, track: Track):
        super().__init__(title=track.name)

        self.track = track

        self.track_input = discord.ui.TextInput(
            label="What would you like to track?", 
            placeholder=track.default_tracking_value)
        self.add_item(self.track_input)

        self.daily_target_input = discord.ui.TextInput(
            label="What's your daily target?",
            placeholder=f"{track.default_daily_target} [must be a number]")
        self.add_item(self.daily_target_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            daily_target = int(self.daily_target_input.value)
        except ValueError:
            await interaction.response.send_message(
                "Daily target must be a valid number, please try again",
                ephemeral=True)
            return
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        user = await ensure_user(interaction.user)

        # TODO: get category by track
        category = await get_category_by_name(self.track.name)

        if category is None:
            await interaction.followup.send(
                "Something went wrong, please try later", ephemeral=True)
            return
        
        await new_goal(
            user_id=user.user_id,
            category_id=category.category_id,
            metric=self.track_input.value,
            target=daily_target,
        )
        
        await interaction.followup.send(f"Your settings were updated!", ephemeral=True)


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    await tree.sync(guild=discord.Object(id=DISCORD_SERVER_ID))

    channel = await client.fetch_channel(SETTINGS_CHANNEL_ID)
    view = TrackSettingsView()
    await channel.send('Pick your goal:', view=view)

    await send_weekly_leaderboard.start()


@client.event
async def on_message(message):
    if message.author == client.user:
        return
        
    if message.attachments:
        user = await ensure_user(message.author)

        category = get_category(message.channel.name)
        if category is None:
            return
        
        goal = await get_goal(category.category_id, user.user_id)
        if goal is None:
            return

        for attchemnt in message.attachments:
            await new_submission(
                user_id=user.user_id,
                goal_id=goal.goal_id,
                proof_url=attchemnt.url,
                amount=0,
            )


# map from a user to it's voice channel join time
VOICE_CHANNELS_JOIN_TIME = {}


async def process_voice_channel_activity(member, before, after):
    member_joins_channel = before.channel is None and after.channel is not None
    member_leaves_channel = before.channel is not None and (after.channel is None or after.channel.name != before.channel.name)
    
    user = await ensure_user(member)

    if member_joins_channel:
        VOICE_CHANNELS_JOIN_TIME[user.user_id] = datetime.utcnow()

    if member_leaves_channel:
        time_joined = VOICE_CHANNELS_JOIN_TIME.pop(user.user_id, None)
        if time_joined is None:
            return
        time_left = datetime.utcnow()
        time_spent = time_left - time_joined
        
        category = await get_category_for_voice(before.channel.name)
        if category is None:
            return
        
        goal = await get_goal(category.category_id, user.user_id)
        if goal is None:
            return
        
        await new_submission(
            user_id=user.user_id,
            goal_id=goal.goal_id,
            proof_url=None,
            amount=time_spent.seconds // 60,
        )


@client.event
async def on_voice_state_update(member, before, after):
    print(member, before, after)
    await process_voice_channel_activity(member, before, after)


tree = app_commands.CommandTree(client)

@tree.command(
    name="submit",
    description="Submit your daily progress",
    guild=discord.Object(id=DISCORD_SERVER_ID),
)
async def submit_command(interaction, amount: int):
    # TODO: handle database errors

    await interaction.response.defer(thinking=True, ephemeral=True)

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

    await interaction.followup.send(f"Your progress is saved!", ephemeral=True)


@tree.command(
    name="stats",
    description="Get personal stats for the last week",
    guild=discord.Object(id=DISCORD_SERVER_ID),
)
async def stats_command(interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)

    statistics = await get_personal_statistics(interaction.user.id)

    msg_parts = [
        f"**Personal stats for the last week **\n"
        f"**{interaction.user.global_name}**\n"
    ] + [
        f"**{category_name}**:\n"
        f"Submissions: {category_stats.submissions_number}\n"
        f"Active days: {category_stats.days_with_submissions}\n"
        for category_name, category_stats in statistics.by_category.items()
    ]

    msg = "\n".join(msg_parts)

    await interaction.followup.send(msg, ephemeral=False)


@tasks.loop(hours=24)
async def send_weekly_leaderboard():
    # TODO: run every hour, but send only after 24 hours from the last report
    print("Sending weekly leaderboard")
    leaderboards = await get_weekly_leaderboard()

    current_date = datetime.now().strftime("%d-%b-%Y")

    msg_parts = [f"**Weekly leaderboard: {current_date}**\n"]

    for category, leaderboard in leaderboards.items():
        msg_parts.append(f"**{category}**")
        for user_id, submissions, days in leaderboard:
            username = (await client.fetch_user(user_id)).global_name
            msg_parts.append(f"{username}: {submissions} submissions, {days} active days")
        msg_parts.append("")

    msg = "\n".join(msg_parts)

    channel = await client.fetch_channel(GENERAL_CHANNEL_ID)
    await channel.send(msg)


async def init():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("Please set the DATABASE_URL environment variable")
    
    await init_db(DATABASE_URL)

    # await clean_database()
    
    discord.utils.setup_logging()
    await client.start(DISCORD_TOKEN)


asyncio.run(init())
