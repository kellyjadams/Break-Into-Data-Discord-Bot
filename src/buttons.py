import asyncio
import logging
from dataclasses import dataclass

import discord

from src.database import (
    get_category_by_name,
    save_user_personal_details,
    new_goal,
    ensure_user,
)
from src.models import User


@dataclass
class Track:
    name: str
    description: str = ""


# Setting up logger
logger = logging.getLogger(__name__)

TRACKS = {
    track.name: track 
    for track in  [
        Track(
            name="Fitness",
            description="Any kind of sport activity",
        ),
        Track(
            name="Coding",
            description="LeetCode, CodeWars, etc.",
        ),
        Track(
            name="Studying",
            description="Reading, learning new things",
        ),
        Track(
            name="Meditation",
            description="Meditation, yoga, etc.",
        ),
        Track(
            name="Content Creation",
            description="Writing, drawing, etc.",
        ),
        Track(
            name="Other",
            description="Any other activity you want to track",
        ),
    ]
}


class TrackSettingsModal(discord.ui.Modal):
    """Adds user's inputs in the goals table"""

    def __init__(self, track: Track, onboarding_required: bool):
        super().__init__(title=track.name)
        self.track = track
        self.onboarding_required = onboarding_required
                
        self.user_name = discord.ui.TextInput(
            label="Your Name",
            placeholder="Enter your name",
            required=True,
        )
        self.email = discord.ui.TextInput(
            label="Email Address",
            placeholder="Enter your email",
            required=True,
        )
        
        self.description_input = discord.ui.TextInput(
            label="Description", required=True, placeholder="Describe your goal here"
        )
        
        if onboarding_required:
            self.add_item(self.user_name)
            self.add_item(self.email)
            
        self.add_item(self.description_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Makes sure the user input a number and not a string"""
        logging.info(f"Goal submission attempt by {interaction.user}")
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Checking user exists just to avoid any tricky edge cases
        # This is not any slower than using get_user,
        # So we can always use `ensure_user` to be safe
        user, category = await asyncio.gather(
            ensure_user(interaction.user),
            get_category_by_name(self.track.name),
        )
        
        if self.onboarding_required:
            await save_user_personal_details(
                interaction.user, 
                self.email.value, 
                self.user_name.value
            )

        if category is None:
            await interaction.followup.send(
                "Something went wrong, please try later", ephemeral=True
            )
            return

        await new_goal(
            user_id=user.user_id,
            category_id=category.category_id,
            goal_description=self.description_input.value,
            metric="",
            target=1,
            frequency="",
        )

        await interaction.followup.send(f"Your settings for {self.track.name} were updated!", ephemeral=True)
        logging.info(f"Goal successfully updated for user {interaction.user}")


class TrackSettingsView(discord.ui.View):
    """Creates a view with the buttons for each track"""

    def __init__(self):
        super().__init__(timeout=None)

        self.category_select = discord.ui.Select(
            placeholder="Choose a Category!",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=track.name,
                    value=track.name,
                    description=track.description,
                )
                for track in TRACKS.values()
            ],
            custom_id="track_select",
            row=0,
        )
        self.add_item(self.category_select)

        self.add_item(discord.ui.Button(
            label="Setup", style=discord.ButtonStyle.primary,
            custom_id="setup_btn",
            row=1,
        ))
        
    async def setup_goals(self, interaction: discord.Interaction):        
        if len(self.category_select.values) == 0:
            await interaction.response.send_message(
                "Please select a category first!",
                ephemeral=True,
            )
            return False
        
        user = await ensure_user(interaction.user)

        track = TRACKS.get(self.category_select.values[0])

        if not track:
            await interaction.response.send_message(
                "Something went wrong, please try again", 
                ephemeral=True,
            )
            logger.error(f'Can\'t find track: {interaction.data.get("custom_id")}')
            return False

        modal = TrackSettingsModal(
            track=track, 
            onboarding_required=user.email is None or user.name is None
        )
        await interaction.response.send_modal(modal)

        return False
    
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return True

        if interaction.data.get("custom_id") == "setup_btn":
            return await self.setup_goals(interaction)
        
        await interaction.response.defer()
        
        return False
        


class OnboardingModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Please enter your info :)")

        self.name = discord.ui.TextInput(
            label="Your Name",
            placeholder="Enter your name",
            required=True,
        )
        self.add_item(self.name)

        self.email = discord.ui.TextInput(
            label="Email Address",
            placeholder="Enter your email",
            required=True,
        )
        self.add_item(self.email)

    async def on_submit(self, interaction):
        # Defer (new_user takes long)
        await interaction.response.defer(ephemeral=True)

        name = self.name.value
        email = self.email.value

        await save_user_personal_details(interaction.user, email, name)

        await interaction.followup.send(
            f"Thanks for submitting, {name}!", ephemeral=True
        )


class OnboardingButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Complete Profile",
            style=discord.ButtonStyle.primary,
            custom_id="submit_info",
        )

    async def callback(self, interaction: discord.Interaction):
        modal = OnboardingModal()
        await interaction.response.send_modal(modal)


class OnboardingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OnboardingButton())


def is_user_activated(user: User):
    """Checks if the user is activated"""
    return bool(user.email)


async def ensure_user_is_activated(
    user: User, interaction: discord.Interaction
) -> bool:
    """Checks if the user is activated
    Sends a message if the user is not activated
    """

    if is_user_activated(user):
        return True

    message = "Please create a profile first:"
    view = OnboardingView()

    if interaction.response.is_done():
        await interaction.followup.send(message, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(message, view=view, ephemeral=True)

    return False
