import discord
import os, dotenv
from datetime import datetime, timedelta
import asyncio
from discord import app_commands
from src.database import (
    init_db,
    get_goal,
    ensure_user,
    get_category,
    new_submission,
    get_user_goals
)
from src.submissions.llm_backfill import parse_submission_message

dotenv.load_dotenv()

DISCORD_TOKEN = os.environ['DISCORD_BOT_TOKEN']
DISCORD_SERVER_ID = os.environ['DISCORD_SERVER_ID']
SUBMISSION_CHANNEL_ID = ['1197314741534736464', '1197259793266638970', '1168693561429069834']

client = discord.Client(
    intents=discord.Intents.all(),
)

tree = app_commands.CommandTree(client)

async def backfill_submissions():  
    #Connect to server and channel
    await tree.sync(guild=discord.Object(id=DISCORD_SERVER_ID))
    for channelid in SUBMISSION_CHANNEL_ID:
        channel = await client.fetch_channel(channelid)
        #Get History of messages
        # Initialize the 'before' parameter to None for the first batch
        one_week_ago = datetime.utcnow() - timedelta(weeks=1)
        before = None
        batch_limit = 100  # Set the batch size
        while True:
            async for message in channel.history(limit=batch_limit, before=before, after=one_week_ago): 
                if message.author == client.user:
                    continue
                
                if message.attachments:
                    user = await ensure_user(message.author)

                    category = get_category(message.channel.name)
                    if category is None:
                        continue

                    goal = await get_goal(category.category_id, user.user_id)
                    if goal is None:
                        continue

                    # for attachment in message.attachments:
                    #     await new_submission(
                    #         user_id=user.user_id,
                    #         goal_id=goal.goal_id,
                    #         proof_url=attachment.url,
                    #         amount=0,
                    #     )

                if message.content:
                    print(message.content)
                    user_goals = await get_user_goals(message.author.id)
                    # print(user_goals)

                    if user_goals:
                        submission_items = await parse_submission_message(
                            message.content,
                            user_goals,
                            message.created_at
                        )

                        print(submission_items)
                        print()

                        if not submission_items:
                            continue

                    # Inserting data
                        # for item in submission_items:
                        #     await new_submission(
                        #         user_id=message.author.id,
                        #         goal_id=item.goal_id,
                        #         proof_url=None,
                        #         amount=item.value or 0,
                        #     )    
                before = message.id

                

@client.event
async def on_ready():
    print('Logged in as', client.user.name)
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("Please set the DATABASE_URL environment variable")

    await init_db(DATABASE_URL)
    await backfill_submissions()
    # await client.close()

client.run(DISCORD_TOKEN)