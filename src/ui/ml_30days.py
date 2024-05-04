import discord
from functools import cache

from src.database import ensure_user, get_category_by_name, new_goal
from src.buttons import ensure_user_is_activated


ROLE_ID = 1236401709719355554
CATEGORY_NAME = "30 Days ML"


@cache
def get_role(guild):
    return guild.get_role(ROLE_ID)


class Challenge30DaysML(discord.ui.View):
    """Creates a view with the buttons for each track"""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="Opt In", style=discord.ButtonStyle.primary,
            custom_id="opt_in",
            row=0,
        ))
        self.add_item(discord.ui.Button(
            label="Opt Out", style=discord.ButtonStyle.secondary,
            custom_id="opt_out",
            row=0,
        ))
        
    async def opt_in(self, interaction: discord.Interaction): 
        """ Opt in to the 30 days ML challenge
        Adds the role for the challenge to the user
          and creates a goal for the user
        """
        await interaction.response.defer(thinking=True, ephemeral=True) 
        
        user = await ensure_user(interaction.user)
        await ensure_user_is_activated(user, interaction)
        
        # if already opted in, do nothing
        roles = [role.id for role in interaction.user.roles]
        if ROLE_ID in roles:
            await interaction.followup.send(
                "You have already opted in to the 30 days ML challenge!",
                ephemeral=True,
            )
            return False
        
        role = get_role(interaction.user.guild)
        await interaction.user.add_roles(role)
        
        await interaction.followup.send(
            "You have opted in to the 30 days ML challenge!",
            ephemeral=True,
        )
        
        category = await get_category_by_name(CATEGORY_NAME)
        
        await new_goal(
            user_id=user.user_id,
            category_id=category.category_id,
            goal_description="",
            metric="",
            target=1,
            frequency="",
        )

        return False
    
    async def opt_out(self, interaction: discord.Interaction):
        """ Opt out of the 30 days ML challenge
        Removes the role for the challenge from the user
        Does not remove the goal
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        role = get_role(interaction.user.guild)
        
        roles = [role.id for role in interaction.user.roles]
        if ROLE_ID not in roles:
            await interaction.followup.send(
                "You have not opted in to the 30 days ML challenge!",
                ephemeral=True,
            )
            return False
        
        await interaction.user.remove_roles(role)
        await interaction.followup.send(
            "You have opted out of the 30 days ML challenge!",
            ephemeral=True,
        )
        
        return False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return True
        
        if interaction.data.get("custom_id") == "opt_in":
            return await self.opt_in(interaction)
        
        if interaction.data.get("custom_id") == "opt_out":
            return await self.opt_out(interaction)
        
        await interaction.response.defer()
        
        return False
    