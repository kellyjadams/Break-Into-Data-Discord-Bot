import discord

from src.database import (
    new_goal,
    ensure_user, 
    get_category_by_name,
)
from src.buttons import ensure_user_is_activated


LEETCODE_CATEGORY_NAME = "_automated_LeetCode"


class ConnectExternalPlatform(discord.ui.View):
    """ Creates a view with the buttons for connecting 
    services like LeetCode, GitHub, etc.
    """

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="Connect LeetCode", style=discord.ButtonStyle.primary,
            custom_id="leetcode",
            row=0,
        ))
        
    async def connect_leetcode(self, interaction: discord.Interaction): 
        await interaction.response.defer(thinking=True, ephemeral=True) 
        
        user = await ensure_user(interaction.user)
        await ensure_user_is_activated(user, interaction)
        
        # TODO: check that the user actually exists on LeetCode
        # TODO: upsert the connected account in the database
        
        await interaction.followup.send(
            "Now your progress will be tracked automatically!",
            ephemeral=True,
        )
        
        category = await get_category_by_name(LEETCODE_CATEGORY_NAME)
        
        await new_goal(
            user_id=user.user_id,
            category_id=category.category_id,
            goal_description="",
            metric="",
            target=1,
            frequency="",
        )

        return False
    
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return True
        
        handler = getattr(self, f"connect_{interaction.data.get('custom_id')}")
        await handler(interaction)

        await interaction.response.defer()
        
        return False
    