import discord


async def setup(bot):
    @bot.tree.command(name="ping", description="Check the bot's latency")
    async def ping(interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")