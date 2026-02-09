# =========================================================
# DISCORD NC KYAMI — TG STYLE PORT (PRODUCTION)
# NC + LOOP + SUDO + DELAY + STATUS
# =========================================================

import discord
from discord.ext import commands
import asyncio, json, os, time
from typing import Dict, Set

# =========================
# CONFIG (TG STYLE)
# =========================
TOKEN = "MTQ2NjA5NDkyMjk4NDU5MTQ4NQ.G8Yacv.XclVmLAde3y745aJXFjKhl6Q23PbFwz5ebq3yA"

OWNER_ID = 1069460715020222514  # <-- your discord user id
SUDO_FILE = "sudo.json"
DEFAULT_DELAY = 0.8

# Example texts like TG RAID_TEXTS
RAID_TEXTS = [
    "×~🌷1🌷×~","~×🌼2🌼×~","××🌻3🌻××","~~🌺4🌺~~","~×🌹5🌹×~",
    "×~🏵️6🏵️×~","~×🪷7🪷×~","××💮8💮××","~~🌸9🌸~~","~×🌷10🌷×~",
]

# =========================
# GLOBAL STATE
# =========================
delay = DEFAULT_DELAY

# Loop tasks per guild or per channel
loop_tasks: Dict[int, asyncio.Task] = {}   # key=channel_id
loop_running_channels: Set[int] = set()

# NC rotation per guild
nc_channels: Dict[int, list[int]] = {}     # key=guild_id -> channel_ids
nc_index: Dict[int, int] = {}              # key=guild_id -> index

# =========================
# SUDO LOAD (TG STYLE)
# =========================
if os.path.exists(SUDO_FILE):
    try:
        with open(SUDO_FILE, "r", encoding="utf-8") as f:
            SUDO_USERS = set(int(x) for x in json.load(f))
    except Exception:
        SUDO_USERS = {OWNER_ID}
else:
    SUDO_USERS = {OWNER_ID}

with open(SUDO_FILE, "w", encoding="utf-8") as f:
    json.dump(list(SUDO_USERS), f, indent=2)

def save_sudo():
    with open(SUDO_FILE, "w", encoding="utf-8") as f:
        json.dump(list(SUDO_USERS), f, indent=2)

# ✅ owner always sudo
SUDO_USERS.add(OWNER_ID)
save_sudo()

# =========================
# PERMISSIONS (TG STYLE)
# =========================
def only_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def only_sudo():
    async def predicate(ctx):
        return ctx.author.id in SUDO_USERS
    return commands.check(predicate)

# =========================
# DISCORD SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# =========================
# LOOPS
# =========================
async def message_loop(channel: discord.TextChannel, base_text: str):
    i = 0
    while True:
        try:
            msg = f"{base_text} {RAID_TEXTS[i % len(RAID_TEXTS)]}"
            await channel.send(msg)
            i += 1
            await asyncio.sleep(delay)
        except discord.Forbidden:
            # missing permission
            await asyncio.sleep(2)
        except discord.HTTPException:
            # rate limit / network fail
            await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(1)

def start_loop(channel: discord.TextChannel, base_text: str):
    if channel.id in loop_tasks:
        loop_tasks[channel.id].cancel()

    loop_running_channels.add(channel.id)
    loop_tasks[channel.id] = asyncio.create_task(message_loop(channel, base_text))

def stop_loop(channel_id: int):
    if channel_id in loop_tasks:
        loop_tasks[channel_id].cancel()
        loop_tasks.pop(channel_id, None)
    loop_running_channels.discard(channel_id)

# =========================
# EVENTS
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

# =========================
# BASIC COMMANDS
# =========================
@bot.command()
@only_sudo()
async def start(ctx):
    await ctx.send("Discord NC Kyami — running ✅")

@bot.command()
@only_sudo()
async def help(ctx):
    await ctx.send(
        "**Commands:**\n"
        "`!setnc #ch1 #ch2 ...` set NC channels\n"
        "`!nc <text>` send once to next channel\n"
        "`!loop <text>` start loop in current channel\n"
        "`!stop` stop loop in current channel\n"
        "`!delay <sec>` set delay\n"
        "`!status` show status\n"
        "`!ping` ping test\n"
        "`!addsudo <@user/id>` add sudo\n"
        "`!delsudo <@user/id>` remove sudo\n"
        "`!listsudo` list sudo\n"
    )

@bot.command()
@only_sudo()
async def ping(ctx):
    t0 = time.time()
    m = await ctx.send("ping...")
    ms = int((time.time() - t0) * 1000)
    await m.edit(content=f"pong {ms}ms")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return await ctx.send("❌ You are not authorized (not SUDO).")
    raise error

# =========================
# NC (NEXT CHANNEL)
# =========================
@bot.command()
@only_sudo()
async def setnc(ctx, *channel_ids: int):
    """Set channels for NC rotation using Channel IDs"""
    if not ctx.guild:
        return await ctx.send("❌ Use inside server, not DM.")

    if not channel_ids:
        return await ctx.send("❌ Example: `!setnc 123 456 789`")

    nc_channels[ctx.guild.id] = list(channel_ids)
    nc_index[ctx.guild.id] = 0

    preview = []
    for cid in channel_ids:
        ch = bot.get_channel(cid)
        preview.append(ch.mention if ch else str(cid))

    await ctx.send("✅ NC channels set: " + ", ".join(preview))

@bot.command()
@only_sudo()
async def nc(ctx, *, text: str = "NC"):
    """Send one message to next channel in rotation + raid text"""
    if not ctx.guild:
        return await ctx.send("❌ Use inside server.")

    ids = nc_channels.get(ctx.guild.id)
    if not ids:
        return await ctx.send("❌ Set channels first: `!setnc #ch1 #ch2`")

    idx = nc_index.get(ctx.guild.id, 0)
    channel_id = ids[idx % len(ids)]
    nc_index[ctx.guild.id] = idx + 1

    channel = bot.get_channel(channel_id)
    if not channel:
        return await ctx.send("❌ Channel not found (bot can't see it).")

    raid = RAID_TEXTS[idx % len(RAID_TEXTS)]
    await channel.send(f"{text} {raid}")

    await ctx.send(f"✅ Sent to next: {channel.mention}")

# =========================
# LOOP CONTROL (TG STYLE)
# =========================
@bot.command()
@only_sudo()
async def loop(ctx, *, text: str):
    """Start loop in current channel"""
    if not isinstance(ctx.channel, discord.TextChannel):
        return await ctx.send("❌ Use inside text channel.")

    start_loop(ctx.channel, text)
    await ctx.send(f"✅ Loop started in {ctx.channel.mention}")

@bot.command()
@only_sudo()
async def stop(ctx):
    stop_loop(ctx.channel.id)
    await ctx.send("🛑 Loop stopped in this channel.")

@bot.command()
@only_sudo()
async def delay(ctx, sec: float = None):
    global delay
    if sec is None:
        return await ctx.send(f"delay={delay}")

    delay = max(0.2, float(sec))
    await ctx.send(f"✅ delay set {delay}")

@bot.command()
@only_sudo()
async def status(ctx):
    s = f"**Active loops:** {len(loop_tasks)}\n"
    for cid in loop_tasks.keys():
        s += f"- <#{cid}>\n"
    await ctx.send(s)

# =========================
# SUDO COMMANDS (TG STYLE)
# =========================
def parse_user_id(arg: str):
    # supports <@123> or plain id
    arg = arg.replace("<@", "").replace(">", "").replace("!", "")
    return int(arg)

@bot.command()
@only_owner()
async def addsudo(ctx, user: str):
    uid = parse_user_id(user)
    SUDO_USERS.add(uid)
    save_sudo()
    await ctx.send("✅ sudo added")

@bot.command()
@only_owner()
async def delsudo(ctx, user: str):
    uid = parse_user_id(user)
    if uid in SUDO_USERS:
        SUDO_USERS.remove(uid)
        save_sudo()
    await ctx.send("✅ sudo removed")

@bot.command()
@only_sudo()
async def listsudo(ctx):
    await ctx.send("SUDO:\n" + "\n".join(map(str, SUDO_USERS)))

# =========================
# RUN
# =========================
if __name__ == "__main__":
    bot.run(TOKEN)
