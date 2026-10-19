import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


BASE_DIR = Path(__file__).resolve().parent.parent
POLLS_PATH = BASE_DIR / "polls.json"

EMOJIS = [
    "1️⃣",
    "2️⃣",
    "3️⃣",
    "4️⃣",
    "5️⃣",
    "6️⃣",
    "7️⃣",
    "8️⃣",
    "9️⃣",
    "🔟",
]


def load_polls():
    if not POLLS_PATH.exists():
        return {}

    try:
        with open(POLLS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_polls(polls):
    with open(POLLS_PATH, "w", encoding="utf-8") as f:
        json.dump(polls, f, indent=4)


class PollView(discord.ui.View):
    def __init__(
        self,
        poll_id,
        question,
        options,
        creator_id,
        votes=None,
        closed=False
    ):
        super().__init__(timeout=None)

        self.poll_id = str(poll_id)
        self.question = question
        self.options = options
        self.creator_id = int(creator_id)
        self.votes = {
            str(user_id): int(option_index)
            for user_id, option_index in (votes or {}).items()
        }
        self.closed = closed

        for index in range(len(options)):
            self.add_item(
                PollButton(
                    poll=self,
                    option_index=index,
                    row=index // 5
                )
            )

        self.add_item(
            ClosePollButton(
                poll=self,
                row=2
            )
        )

        if self.closed:
            for item in self.children:
                item.disabled = True

    def get_counts(self):
        counts = [0] * len(self.options)

        for option_index in self.votes.values():
            if 0 <= option_index < len(counts):
                counts[option_index] += 1

        return counts

    def create_embed(self):
        counts = self.get_counts()
        total_votes = len(self.votes)

        embed = discord.Embed(
            title="📊 Poll",
            description=f"**{self.question}**",
            color=discord.Color.blurple() if not self.closed else discord.Color.greyple()
        )

        lines = []

        for index, option in enumerate(self.options):
            count = counts[index]
            percentage = (count / total_votes * 100) if total_votes else 0

            lines.append(
                f"{EMOJIS[index]} **{option}** — "
                f"`{count}` vote{'s' if count != 1 else ''} "
                f"({percentage:.1f}%)"
            )

        embed.add_field(
            name="Options",
            value="\n".join(lines),
            inline=False
        )

        embed.add_field(
            name="Total Votes",
            value=str(total_votes),
            inline=True
        )

        embed.add_field(
            name="Status",
            value="🔴 Closed" if self.closed else "🟢 Open",
            inline=True
        )

        if self.closed:
            embed.set_footer(text="This poll is closed.")
        else:
            embed.set_footer(
                text="Click an option to vote • You can change your vote."
            )

        return embed

    def save(self, channel_id, message_id, outcome_message_id=None):
        polls = load_polls()

        existing = polls.get(self.poll_id, {})

        polls[self.poll_id] = {
            "guild_id": existing.get("guild_id"),
            "channel_id": int(channel_id),
            "message_id": int(message_id),
            "outcome_message_id": outcome_message_id,
            "creator_id": self.creator_id,
            "question": self.question,
            "options": self.options,
            "votes": self.votes,
            "closed": self.closed
        }

        save_polls(polls)

    async def update_message(self, interaction):
        await interaction.message.edit(
            embed=self.create_embed(),
            view=self
        )

        self.save(
            channel_id=interaction.channel_id,
            message_id=interaction.message.id
        )


class PollButton(discord.ui.Button):
    def __init__(self, poll, option_index, row):
        self.poll = poll
        self.option_index = option_index

        super().__init__(
            label=str(option_index + 1),
            emoji=EMOJIS[option_index],
            style=discord.ButtonStyle.secondary,
            custom_id=f"poll:{poll.poll_id}:option:{option_index}",
            row=row
        )

    async def callback(self, interaction: discord.Interaction):
        if self.poll.closed:
            await interaction.response.send_message(
                "❌ This poll is closed.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)
        previous_vote = self.poll.votes.get(user_id)

        self.poll.votes[user_id] = self.option_index

        option_name = self.poll.options[self.option_index]

        if previous_vote is None:
            message = f"✅ You voted for **{option_name}**."
        elif previous_vote == self.option_index:
            message = f"ℹ️ You're already voting for **{option_name}**."
        else:
            old_option = self.poll.options[previous_vote]
            message = (
                f"🔄 Your vote changed from **{old_option}** "
                f"to **{option_name}**."
            )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )

        await self.poll.update_message(interaction)


class ClosePollButton(discord.ui.Button):
    def __init__(self, poll, row):
        self.poll = poll

        super().__init__(
            label="Close Poll",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id=f"poll:{poll.poll_id}:close",
            row=row
        )

    async def callback(self, interaction: discord.Interaction):
        if self.poll.closed:
            await interaction.response.send_message(
                "❌ This poll is already closed.",
                ephemeral=True
            )
            return

        if interaction.user.id != self.poll.creator_id:
            await interaction.response.send_message(
                "❌ Only the person who created the poll can close it.",
                ephemeral=True
            )
            return

        self.poll.closed = True

        for item in self.poll.children:
            item.disabled = True

        polls = load_polls()
        poll_data = polls.get(self.poll.poll_id, {})

        channel_id = poll_data.get("channel_id", interaction.channel_id)
        message_id = poll_data.get("message_id", interaction.message.id)

        channel = interaction.client.get_channel(channel_id)

        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(channel_id)
            except discord.HTTPException:
                channel = None

        outcome_message = None

        if channel is not None:
            counts = self.poll.get_counts()
            total_votes = len(self.poll.votes)

            result_lines = []

            for index, option in enumerate(self.poll.options):
                count = counts[index]
                percentage = (
                    count / total_votes * 100
                    if total_votes
                    else 0
                )

                result_lines.append(
                    f"{EMOJIS[index]} **{option}** — "
                    f"`{count}` vote{'s' if count != 1 else ''} "
                    f"({percentage:.1f}%)"
                )

            outcome_embed = discord.Embed(
                title="📊 Poll Results",
                description=f"**{self.poll.question}**",
                color=discord.Color.green()
            )

            outcome_embed.add_field(
                name="Final Results",
                value="\n".join(result_lines),
                inline=False
            )

            outcome_embed.add_field(
                name="Total Votes",
                value=str(total_votes),
                inline=True
            )

            if total_votes:
                highest = max(counts)
                winners = [
                    self.poll.options[index]
                    for index, count in enumerate(counts)
                    if count == highest
                ]

                if len(winners) == 1:
                    result_text = f"🏆 **{winners[0]}**"
                else:
                    result_text = "🤝 **Tie:** " + ", ".join(
                        f"**{winner}**"
                        for winner in winners
                    )
            else:
                result_text = "No votes were cast."

            outcome_embed.add_field(
                name="Outcome",
                value=result_text,
                inline=False
            )

            outcome_embed.set_footer(
                text=f"Poll closed by {interaction.user.display_name}"
            )

            outcome_message = await channel.send(
                embed=outcome_embed
            )

        if outcome_message:
            self.poll.save(
                channel_id=channel_id,
                message_id=message_id,
                outcome_message_id=outcome_message.id
            )
        else:
            self.poll.save(
                channel_id=channel_id,
                message_id=message_id
            )

        await interaction.response.edit_message(
            embed=self.poll.create_embed(),
            view=self.poll
        )


class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def restore_polls(self):
        polls = load_polls()

        for poll_id, data in polls.items():
            if data.get("closed"):
                continue

            try:
                view = PollView(
                    poll_id=poll_id,
                    question=data["question"],
                    options=data["options"],
                    creator_id=data["creator_id"],
                    votes=data.get("votes", {}),
                    closed=False
                )

                self.bot.add_view(view)
            except (KeyError, TypeError, ValueError):
                continue

    @app_commands.command(
        name="poll",
        description="Create a poll with up to 10 options."
    )

    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    
    @app_commands.describe(
        question="The question for the poll.",
        option1="Option 1.",
        option2="Option 2.",
        option3="Option 3.",
        option4="Option 4.",
        option5="Option 5.",
        option6="Option 6.",
        option7="Option 7.",
        option8="Option 8.",
        option9="Option 9.",
        option10="Option 10."
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
        option5: str | None = None,
        option6: str | None = None,
        option7: str | None = None,
        option8: str | None = None,
        option9: str | None = None,
        option10: str | None = None
    ):
        options = [
            option1,
            option2,
            option3,
            option4,
            option5,
            option6,
            option7,
            option8,
            option9,
            option10
        ]

        options = [option for option in options if option]

        if len(question) > 256:
            await interaction.response.send_message(
                "❌ The question must be 256 characters or less.",
                ephemeral=True
            )
            return

        for index, option in enumerate(options):
            if len(option) > 100:
                await interaction.response.send_message(
                    f"❌ Option {index + 1} must be 100 characters or less.",
                    ephemeral=True
                )
                return

        poll_id = str(interaction.id)

        view = PollView(
            poll_id=poll_id,
            question=question,
            options=options,
            creator_id=interaction.user.id
        )

        await interaction.response.send_message(
            embed=view.create_embed(),
            view=view
        )

        message = await interaction.original_response()

        polls = load_polls()

        polls[poll_id] = {
            "guild_id": interaction.guild_id,
            "channel_id": interaction.channel_id,
            "message_id": message.id,
            "outcome_message_id": None,
            "creator_id": interaction.user.id,
            "question": question,
            "options": options,
            "votes": {},
            "closed": False
        }

        save_polls(polls)


async def setup(bot):
    cog = Poll(bot)
    await bot.add_cog(cog)
    await cog.restore_polls()
