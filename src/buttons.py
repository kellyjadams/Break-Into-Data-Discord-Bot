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

    questions_needed: list
    default_tracking_metric: str
    default_daily_target: str


# Setting up logger
logger = logging.getLogger(__name__)

TRACKS = {
    track.name: track for track in [
        Track(name="Fitness",
              questions_needed=['description', 'metric', 'target', 'frequency'],
              default_tracking_metric="e.g. miles, minutes ",
              default_daily_target='e.g.30'),
        Track(name="Coding",
              questions_needed=['description', 'metric', 'target', 'frequency'],
              default_tracking_metric="e.g. problems, minutes", 
              default_daily_target='e.g. 3 or 5'),
        Track(name="Studying",
              questions_needed=['description', 'metric', 'target', 'frequency'],
              default_tracking_metric="e.g. minutes, chapters", 
              default_daily_target='60 or 2'),
        Track(name="Meditation",
              questions_needed=['description', 'metric', 'target', 'frequency'],
              default_tracking_metric="e.g. minutes, sessions",
              default_daily_target='60 or 2'),
        Track(name="Content Creation",
              questions_needed=['description', 'metric', 'target', 'frequency'],
              default_tracking_metric="e.g. posts, videos, blogs", 
              default_daily_target='1 or 2'),
        Track(name="Other",
              questions_needed=['description', 'metric', 'target', 'frequency'],
              default_tracking_metric="Smiles", 
              default_daily_target=10),
    ]
}


class TrackSettingsModal(discord.ui.Modal):
    """ Adds user's inputs in the goals table """
    def __init__(self, track: Track):
        super().__init__(title=track.name)
        self.track = track

        if 'description' in track.questions_needed:
            # New field for their
            self.description_input = discord.ui.TextInput(
                label="Description",
                required=True,
                placeholder="Describe your goal!")
            self.add_item(self.description_input)


        if 'metric' in track.questions_needed:
            self.metric_input = discord.ui.TextInput(
                label="What is your metric?",
                placeholder=track.default_tracking_metric)
            self.add_item(self.metric_input)


        target_map = {
            'Coding': 'Daily coding goals? 5 problems/2 hours',
            'Meditation': 'Set your meditation goal',
            'Fitness': 'What is your exercise target?',
            'Studying': 'Set your study goal',
            'Content Creation': 'How much content to make?',
            'Other': 'Set your Number to measure.'
        }

        if 'target' in track.questions_needed:
            self.daily_target_input = discord.ui.TextInput(
                label=target_map[track.name],
                placeholder=f"{track.default_daily_target} (it must be a number)")
            self.add_item(self.daily_target_input)

        # New field for frequency
        if 'frequency' in track.questions_needed:
            self.frequency_input = discord.ui.TextInput(
                label="What is the frequency per week? ",
                placeholder="e.g. 4, 5 (times a week) ")
            self.add_item(self.frequency_input)

    async def on_submit(self, interaction: discord.Interaction):
        """ Makes sure the user input a number and not a string """
        logging.info(f'Goal submission attempt by {interaction.user}')
        try:
            daily_target = int(self.daily_target_input.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "Daily target must be a valid number, please try again",
                ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)
    
        # Checking user exists just to avoid any tricky edge cases
        # This is not any slower than using get_user,
        # So we can always use `ensure_user` to be safe
        user, category = await asyncio.gather(
            ensure_user(interaction.user),
            get_category_by_name(self.track.name)
        )

        if category is None:
            await interaction.followup.send(
                "Something went wrong, please try later", ephemeral=True)
            return

        await new_goal(
            user_id=user.user_id,
            category_id=category.category_id,
            goal_description=self.description_input.value if 'description' in self.track.questions_needed else '',
            metric=self.metric_input.value if 'metric' in self.track.questions_needed else self.track.name,
            target=daily_target,
            frequency=self.frequency_input.value if 'frequency' in self.track.questions_needed else 'daily'
        )

        await interaction.followup.send("Your settings were updated!", ephemeral=True)
        logging.info(f'Goal successfully updated for user {interaction.user}')


class TrackSettingsView(discord.ui.View):
    """ Creates a view with the buttons for each track """
    def __init__(self):
        super().__init__(timeout=None)

        for track in TRACKS.values():
            self.add_button(track)

    def add_button(self, track: Track):
        btn = discord.ui.Button(
            label=track.name,
            style=discord.ButtonStyle.secondary, 
            custom_id=track.name
        )
        self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return True
        
        user = await ensure_user(interaction.user)
        if not await ensure_user_is_activated(user, interaction):
            return False
        
        track = TRACKS.get(interaction.data.get('custom_id'))

        if not track:
            interaction.response.send_message(
                "Something went wrong, please try again", ephemeral=True)
            logger.error(f'Can\'t find track: {interaction.data.get("custom_id")}')
            return False
        
        modal = TrackSettingsModal(track)
        await interaction.response.send_modal(modal)
        
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

        await interaction.followup.send(f"Thanks for submitting, {name}!", ephemeral=True)


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
    """ Checks if the user is activated """
    return bool(user.email)


async def ensure_user_is_activated(user: User, interaction: discord.Interaction) -> bool:
    """ Checks if the user is activated
    Sends a message if the user is not activated
    """
    
    if is_user_activated(user):
        return True
    
    message = "Please create a profile first:"
    view = OnboardingView()
        
    if interaction.response.is_done():
        await interaction.followup.send(
            message, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(
            message, view=view, ephemeral=True)
        
    return False