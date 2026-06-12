import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time
import os
import json
from threading import Thread

from config import *
from generator import RobloxGen
from proxy_manager import ProxyManager
from captcha_solver import CaptchaSolver

SAVED_LIST_PATH = "saved_accounts.json"


class RobloxBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.pm = ProxyManager(PROXY_MODE, PROXY_URL, PROXY_LIST_FILE)
        self.cs = CaptchaSolver(CAPTCHA_SERVICE, CAPTCHA_API_KEY)
        self.gen = RobloxGen(self.pm, self.cs)

        # Generation queue
        self.queue = asyncio.Queue()
        self.queue_active = False
        self.total_generated = 0

        # Load saved accounts
        self.saved_accounts = []
        self._load_saved()

        # Pending manual captcha tokens
        self.pending_captcha = {}

    def _load_saved(self):
        if os.path.exists(SAVED_LIST_PATH):
            try:
                with open(SAVED_LIST_PATH, "r") as f:
                    self.saved_accounts = json.load(f)
                print(f"[+] Loaded {len(self.saved_accounts)} saved accounts")
            except:
                self.saved_accounts = []

    def _save_accounts(self):
        with open(SAVED_LIST_PATH, "w") as f:
            json.dump(self.saved_accounts, f, indent=2)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        print(f"[+] Commands synced")

    async def on_ready(self):
        print(f"[+] Bot online as {self.user}")
        self.loop.create_task(self._process_queue())

    async def _process_queue(self):
        """Background task that processes the generation queue."""
        await self.wait_until_ready()
        self.queue_active = True
        while True:
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=30)
            except asyncio.TimeoutError:
                continue

            ctx, count, prefix, password, channel = item

            # Run generation in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self.gen.bulk_create, count, prefix, password
            )

            successful = [a for a in results if a.get("success")]
            failed = [a for a in results if not a.get("success")]

            self.total_generated += len(successful)
            for acc in successful:
                self.saved_accounts.append(acc)
            self._save_accounts()

            # Send results
            embed = discord.Embed(
                title="✅ Generation Complete",
                color=discord.Color.green() if successful else discord.Color.red()
            )
            embed.add_field(name="Created", value=str(len(successful)), inline=True)
            embed.add_field(name="Failed", value=str(len(failed)), inline=True)
            embed.add_field(name="Total Generated", value=str(self.total_generated), inline=True)

            if successful:
                text = "\n".join([f"`{a['username']}:{a['password']}`" for a in successful[:10]])
                if len(successful) > 10:
                    text += f"\n... and {len(successful)-10} more"
                embed.add_field(name="Accounts", value=text or "None", inline=False)

            await channel.send(embed=embed)
            self.queue.task_done()


bot = RobloxBot()


# ====== SLASH COMMANDS ======

@bot.tree.command(name="gen", description="Generate Roblox accounts")
@app_commands.describe(
    count="How many accounts (1-50)",
    prefix="Username prefix (default: Test)",
    password="Custom password (optional)"
)
async def gen(interaction: discord.Interaction, count: app_commands.Range[int, 1, 50] = 1,
              prefix: str = "Test", password: str = None):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    await interaction.response.send_message(
        f"⏳ **Queued {count} account(s)** with prefix `{prefix}`\n"
        f"You'll be notified when done.", ephemeral=True
    )

    await bot.queue.put((interaction, count, prefix, password, interaction.channel))


@bot.tree.command(name="bulk", description="Generate a bulk batch (10-15 accounts fast)")
@app_commands.describe(
    amount="10-15 accounts typically",
    prefix="Username prefix"
)
async def bulk(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 50] = 10,
               prefix: str = "BulkTest"):
    """Convenience command for bulk generation - typically 10-15 at a time."""
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    await interaction.response.send_message(
        f"⚡ **Bulk generating {amount} accounts** with prefix `{prefix}`...\n"
        f"Results will appear in this channel.", ephemeral=True
    )

    await bot.queue.put((interaction, amount, prefix, None, interaction.channel))


@bot.tree.command(name="list", description="View saved accounts from the bank")
@app_commands.describe(
    page="Page number (25 accounts per page)"
)
async def list_accs(interaction: discord.Interaction, page: int = 1):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    if not bot.saved_accounts:
        return await interaction.response.send_message("📭 No saved accounts yet. Use `/gen` first.", ephemeral=True)

    per_page = 25
    total = len(bot.saved_accounts)
    max_page = (total + per_page - 1) // per_page
    page = max(1, min(page, max_page))

    start = (page - 1) * per_page
    end = start + per_page
    batch = bot.saved_accounts[start:end]

    embed = discord.Embed(
        title=f"📋 Saved Accounts Bank",
        description=f"**Total:** {total} accounts | **Page {page}/{max_page}**",
        color=discord.Color.blue()
    )

    lines = []
    for acc in batch:
        uid = acc.get("user_id", "?")
        lines.append(f"`{acc['username']}:{acc['password']}` | ID: {uid}")

    embed.add_field(name=f"Accounts {start+1}-{end}", value="\n".join(lines) or "None", inline=False)
    embed.set_footer(text=f"Page {page}/{max_page} • Use /export to download all")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="export", description="Export all saved accounts as a file")
async def export(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    if not bot.saved_accounts:
        return await interaction.response.send_message("📭 No accounts to export.", ephemeral=True)

    # Create a formatted text file
    lines = ["Username:Password | UserID"]
    lines.append("=" * 50)
    for acc in bot.saved_accounts:
        uid = acc.get("user_id", "N/A")
        lines.append(f"{acc['username']}:{acc['password']} | {uid}")

    content = "\n".join(lines)
    filename = f"roblox_accounts_{int(time.time())}.txt"

    # Discord has 25MB file limit, accounts file is tiny
    with open(filename, "w") as f:
        f.write(content)

    await interaction.response.send_message(
        f"📦 **{len(bot.saved_accounts)} accounts exported!**",
        file=discord.File(filename),
        ephemeral=False
    )
    os.remove(filename)


@bot.tree.command(name="clearlist", description="Clear ALL saved accounts from the bank")
async def clearlist(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    count = len(bot.saved_accounts)
    bot.saved_accounts = []
    bot._save_accounts()

    embed = discord.Embed(
        title="🗑️ Accounts Cleared",
        description=f"Removed **{count}** accounts from the bank.",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="status", description="Check generator status")
async def status(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    embed = discord.Embed(title="📊 Generator Status", color=discord.Color.blue())
    embed.add_field(name="Proxy Mode", value=PROXY_MODE, inline=True)
    embed.add_field(name="Captcha Service", value=CAPTCHA_SERVICE, inline=True)
    embed.add_field(name="Total Generated", value=str(bot.total_generated), inline=True)
    embed.add_field(name="Saved Accounts", value=str(len(bot.saved_accounts)), inline=True)
    embed.add_field(name="Queue Size", value=str(bot.queue.qsize()), inline=True)
    embed.add_field(name="Queue Running", value=str(bot.queue_active), inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="captcha", description="Submit a manual captcha token (if using manual mode)")
@app_commands.describe(token="The captcha token you solved")
async def captcha_submit(interaction: discord.Interaction, token: str):
    """For manual captcha solving - submit the token here."""
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    # Store in a global dict that the generator checks
    bot.pending_captcha[interaction.user.id] = token
    await interaction.response.send_message(
        f"✅ Captcha token received and stored. The generator will use it on the next attempt.",
        ephemeral=True
    )


@bot.tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Roblox Generator Commands",
        description="Authorized security assessment tool",
        color=discord.Color.purple()
    )
    embed.add_field(name="/gen count prefix password",
                    value="Generate accounts (1-50 at a time)", inline=False)
    embed.add_field(name="/bulk amount prefix",
                    value="Quick bulk generate (default 10)", inline=False)
    embed.add_field(name="/list page",
                    value="View saved accounts bank (25 per page)", inline=False)
    embed.add_field(name="/export",
                    value="Download all accounts as .txt file", inline=False)
    embed.add_field(name="/clearlist",
                    value="Delete all saved accounts", inline=False)
    embed.add_field(name="/captcha token",
                    value="Submit manual captcha token", inline=False)
    embed.add_field(name="/status",
                    value="Check bot health and stats", inline=False)
    await interaction.response.send_message(embed=embed)


# Fix the bulk_create method in generator.py to work as expected
def bulk_create(self, count, prefix="Test", password=None):
    """Create multiple accounts."""
    results = []
    for i in range(count):
        uname = f"{prefix}{random.randint(10000, 99999)}{random.randint(100, 999)}"
        result = self.create(username=uname, password=password)
        results.append(result)
        if result.get("success"):
            print(f"[+] Created: {result['username']}:{result['password']}")
        else:
            print(f"[-] Failed: {result.get('error')}")
        if i < count - 1:
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    return results

# Monkey-patch it onto the generator
RobloxGen.bulk_create = bulk_create


# === KEEP ALIVE (required for Render free tier) ===
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("[!] DISCORD_TOKEN not set!")
        exit(1)
    keep_alive()  # Keep Render free tier awake
    bot.run(DISCORD_TOKEN)