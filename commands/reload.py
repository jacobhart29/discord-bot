from typing import Optional

import discord
from discord import app_commands


async def setup(bot):
    @bot.tree.command(name="reload", description="Reload command files (owner only)")
    @app_commands.describe(file="One command file to reload, like ping (leave empty for all)")
    async def reload(interaction: discord.Interaction, file: Optional[str] = None):
        if not await bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "Only the bot owner can use this.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        name = file[:-3] if file and file.endswith(".py") else file
        results = await bot.reload_command_files(name)
        await bot.tree.sync()

        lines = [
            f"{label}: {', '.join(items)}" for label, items in results.items() if items
        ]
        await interaction.followup.send("\n".join(lines) or "Nothing to reload.")