import os

import discord
from discord import app_commands


class LinkButtons(discord.ui.View):
    def __init__(self, repo_url, profile_url):
        super().__init__()
        self.add_item(discord.ui.Button(label="GitHub Repo", url=repo_url))
        self.add_item(discord.ui.Button(label="My Profile", url=profile_url))


async def setup(bot):
    repo_url = os.getenv("REPO_URL")
    profile_url = os.getenv("PROFILE_URL")
    if not repo_url or not profile_url:
        raise RuntimeError("REPO_URL and PROFILE_URL must be set in .env")

    @bot.tree.command(name="links", description="Get the GitHub repo and profile links")
    async def links(interaction: discord.Interaction):
        await interaction.response.send_message(
            "Here you go:", view=LinkButtons(repo_url, profile_url)
        )