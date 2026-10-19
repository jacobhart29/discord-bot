import discord
from discord import app_commands
from discord.ext import commands


class Permissions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="permissions",
        description="Shows a member's permissions in this server."
    )
    @app_commands.describe(
        member="The member whose permissions you want to check."
    )
    async def permissions(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None
    ):
        if member is None:
            member = interaction.user

        if member.id != interaction.user.id:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ You need **Administrator** permission to check "
                    "another member's permissions.",
                    ephemeral=True
                )
                return

        permissions = member.guild_permissions

        permission_names = {
            "administrator": "Administrator",
            "manage_guild": "Manage Server",
            "manage_channels": "Manage Channels",
            "manage_roles": "Manage Roles",
            "manage_messages": "Manage Messages",
            "manage_webhooks": "Manage Webhooks",
            "manage_threads": "Manage Threads",
            "manage_permissions": "Manage Permissions",
            "kick_members": "Kick Members",
            "ban_members": "Ban Members",
            "moderate_members": "Timeout Members",
            "mention_everyone": "Mention Everyone",
            "view_audit_log": "View Audit Log",
            "view_channel": "View Channels",
            "send_messages": "Send Messages",
            "send_messages_in_threads": "Send Messages in Threads",
            "embed_links": "Embed Links",
            "attach_files": "Attach Files",
            "read_message_history": "Read Message History",
            "add_reactions": "Add Reactions",
            "use_external_emojis": "Use External Emojis",
            "use_external_stickers": "Use External Stickers",
            "connect": "Connect to Voice",
            "speak": "Speak",
            "mute_members": "Mute Members",
            "deafen_members": "Deafen Members",
            "move_members": "Move Members",
            "use_voice_activation": "Use Voice Activity",
            "change_nickname": "Change Nickname",
            "manage_nicknames": "Manage Nicknames",
            "create_instant_invite": "Create Invites",
        }

        allowed = []
        denied = []

        for attribute, name in permission_names.items():
            if getattr(permissions, attribute, False):
                allowed.append(f"✅ {name}")
            else:
                denied.append(f"❌ {name}")

        embed = discord.Embed(
            title=f"Permissions — {member.display_name}",
            color=discord.Color.green()
        )

        if permissions.administrator:
            embed.description = (
                f"{member.mention} has **Administrator** permission, "
                "which grants all permissions."
            )
        else:
            embed.add_field(
                name="Allowed",
                value="\n".join(allowed) or "None",
                inline=False
            )

            embed.add_field(
                name="Denied",
                value="\n".join(denied) or "None",
                inline=False
            )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}"
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Permissions(bot))
