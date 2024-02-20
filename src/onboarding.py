import discord
from src.database import save_user_personal_details

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
        super().__init__(label="Complete Profile", 
                         style=discord.ButtonStyle.primary, custom_id="submit_info")

    async def callback(self, interaction: discord.Interaction):
        modal = OnboardingModal()
        await interaction.response.send_modal(modal)

class OnboardingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OnboardingButton())
