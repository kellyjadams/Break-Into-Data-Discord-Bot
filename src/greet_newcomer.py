import json

import discord

with open('./src/data/welcome_messages.json', 'r') as f:
    welcome_messages = json.load(f)
counter = 0

async def greet_newcomer(member):
    global counter
    system_channel = member.guild.system_channel

    if system_channel is None:
        return
    
    title = welcome_messages['titles'][counter]
    message = welcome_messages['messages'][counter].format(member=member.mention)
    counter = (counter + 1) % len(welcome_messages['messages'])
    
    embed = discord.Embed(
        title=title,
        description=message,
        color=discord.Color.random(),
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text=f"👥 You are member #{member.guild.member_count} in this server!")

    await system_channel.send(embed=embed)