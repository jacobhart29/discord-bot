import json
import os
from datetime import datetime, timezone
from pathlib import Path
import requests

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
ONLINE_CONFIG_URL = os.getenv("ONLINE_CONFIG_URL")

BASE_DIR = Path(__file__).parent
COMMANDS_DIR = BASE_DIR / "commands"
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "status_interval": 30,
    "activity_type": "watching",
    "statuses": ["{servers} servers"],
}

ACTIVITY_TYPES = {
    "playing": discord.ActivityType.playing,
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
}


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except (OSError, json.JSONDecodeError) as e:
        print(f"Could not read config.json ({e}); using defaults")
        return DEFAULT_CONFIG


def update_config_from_online():
    print("Checking for online configuration updates...")
    try:
        response = requests.get(ONLINE_CONFIG_URL, timeout=10)
        response.raise_for_status()
        
        cleaned_text = response.text.strip()
        if not cleaned_text:
            print("Online file is empty. Skipping update.")
            return
            
        online_config = json.loads(cleaned_text)
        
        local_config = {}
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    local_config = json.load(f)
            except json.JSONDecodeError:
                pass
        
        if online_config != local_config:
            print("Changes detected! Overwriting local config.json with remote version.")
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(online_config, f, indent=4)
        else:
            print("Configuration is up to date. No changes made.")
            
    except requests.RequestException as e:
        print(f"Failed to fetch online config: {e}. Starting with existing configuration.")
    except json.JSONDecodeError as e:
        print(f"Online file was not valid JSON ({e}). Starting with existing configuration.")


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default(),
        )
        self.started_at = datetime.now(timezone.utc)
        self.command_files = {}

    def command_file_names(self):
        return sorted(
            p.stem for p in COMMANDS_DIR.glob("*.py") if not p.stem.startswith("_")
        )

    def _tree_names(self):
        return {c.name for c in self.tree.get_commands()}

    async def load_command_file(self, stem):
        before = self._tree_names()
        await self.load_extension(f"commands.{stem}")
        self.command_files[stem] = sorted(self._tree_names() - before)

    async def unload_command_file(self, stem):
        await self.unload_extension(f"commands.{stem}")
        for name in self.command_files.pop(stem, []):
            self.tree.remove_command(name)

    async def reload_command_file(self, stem):
        for name in self.command_files.get(stem, []):
            self.tree.remove_command(name)
        before = self._tree_names()
        await self.reload_extension(f"commands.{stem}")
        self.command_files[stem] = sorted(self._tree_names() - before)

    async def reload_command_files(self, only=None):
        results = {"loaded": [], "reloaded": [], "unloaded": [], "failed": []}
        on_disk = set(self.command_file_names())
        loaded = set(self.command_files)

        if only:
            if only not in on_disk and only not in loaded:
                results["failed"].append(f"{only}: not found")
                return results
            targets = {only}
        else:
            targets = on_disk | loaded
        targets.discard("reload")

        for stem in sorted(targets):
            try:
                if stem not in on_disk:
                    await self.unload_command_file(stem)
                    results["unloaded"].append(stem)
                elif stem in loaded:
                    await self.reload_command_file(stem)
                    results["reloaded"].append(stem)
                else:
                    await self.load_command_file(stem)
                    results["loaded"].append(stem)
            except Exception as e:
                results["failed"].append(f"{stem}: {e}")
        return results

    async def setup_hook(self):
        for stem in self.command_file_names():
            try:
                await self.load_command_file(stem)
                print(f"Loaded command file: {stem}.py")
            except Exception as e:
                print(f"Failed to load {stem}.py: {e}")
        await self.tree.sync()
        rotate_status.start()


bot = Bot()


@tasks.loop(seconds=DEFAULT_CONFIG["status_interval"])
async def rotate_status():
    cfg = load_config()

    interval = max(15, int(cfg["status_interval"]))
    if rotate_status.seconds != interval:
        rotate_status.change_interval(seconds=interval)

    guilds = bot.guilds
    up = int((datetime.now(timezone.utc) - bot.started_at).total_seconds())
    days, rem = divmod(up, 86400)
    hours, rem = divmod(rem, 3600)
    stats = {
        "servers": len(guilds),
        "members": f"{sum(g.member_count or 0 for g in guilds):,}",
        "channels": f"{sum(len(g.channels) for g in guilds):,}",
        "ping": round(bot.latency * 1000),
        "uptime": f"{days}d {hours}h {rem // 60}m",
    }

    templates = cfg["statuses"] or DEFAULT_CONFIG["statuses"]
    template = templates[rotate_status.current_loop % len(templates)]
    try:
        text = template.format(**stats)
    except (KeyError, IndexError, ValueError):
        text = template

    activity_type = ACTIVITY_TYPES.get(cfg["activity_type"], discord.ActivityType.watching)
    await bot.change_presence(activity=discord.Activity(type=activity_type, name=text))


@rotate_status.before_loop
async def before_rotate_status():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Missing DISCORD_TOKEN in .env")
        
    update_config_from_online()
    bot.run(TOKEN)
