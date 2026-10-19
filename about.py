import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone


class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="about",
        description="Shows information about the bot."
    )
    async def about(self, interaction: discord.Interaction):
        uptime = datetime.now(timezone.utc) - self.bot.started_at

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        command_count = len(self.bot.tree.get_commands())

        embed = discord.Embed(
            title="About the Bot",
            description="Information about this Discord bot.",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🤖 Bot",
            value=self.bot.user.mention if self.bot.user else "Unknown",
            inline=True
        )

        embed.add_field(
            name="🖥️ Servers",
            value=f"{len(self.bot.guilds):,}",
            inline=True
        )

        embed.add_field(
            name="⚡ Latency",
            value=f"{round(self.bot.latency * 1000)} ms",
            inline=True
        )

        embed.add_field(
            name="📋 Commands",
            value=f"{command_count:,}",
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=f"{days}d {hours}h {minutes}m {seconds}s",
            inline=True
        )

        embed.add_field(
            name="🐍 Python",
            value="3.11",
            inline=True
        )

        embed.set_footer(
            text=f"Requested by {interaction.user}"
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(About(bot))
