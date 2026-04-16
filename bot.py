import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# Load local .env if it exists, but environmental variables in Render take priority
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:5000/api/messages')
MIN_LENGTH = 10
MONITORED_CHANNELS = [] 
NOTIFY_USER_ID = 1479214179146535096

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found! Make sure to set it in Render Environment Variables.")
    # In local testing, you might want to exit, but let's just log for now
    # exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def send_to_dashboard(data):
    """Send flagged message to your web dashboard"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DASHBOARD_URL, json=data) as response:
                if response.status == 200:
                    print(f"✅ Logged to Dashboard: {data['user']['username']}")
                else:
                    print(f"❌ Dashboard error: {response.status}")
    except Exception as e:
        print(f"❌ Connection to Dashboard failed: {e}")

async def send_dm_report(message, role):
    """Send a DM report to the notify user"""
    try:
        notify_user = await bot.fetch_user(NOTIFY_USER_ID)
        
        embed = discord.Embed(
            title="🚨 Message Flagged & Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now(datetime.timezone.utc)
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(name="👤 User", value=f"{message.author.mention} (`{message.author.name}`)", inline=True)
        embed.add_field(name="🏷️ Role", value=role.upper(), inline=True)
        embed.add_field(name="📝 User ID", value=f"`{message.author.id}`", inline=True)
        embed.add_field(name="💬 Message", value=f"```{message.content[:1000]}```", inline=False)
        embed.add_field(name="📊 Length", value=f"{len(message.content)} characters", inline=True)
        embed.add_field(name="📱 Channel", value=f"#{message.channel.name}", inline=True)
        embed.add_field(name="🖥️ Server", value=message.guild.name, inline=True)
        embed.set_footer(text=f"Message ID: {message.id}")
        
        await notify_user.send(embed=embed)
    except Exception as e:
        print(f"❌ DM failed: {e}")

@bot.event
async def on_ready():
    print(f"🤖 Bot online: {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)

    if message.channel.id not in MONITORED_CHANNELS:
        return

    if len(message.content) > MIN_LENGTH:
        user = message.author
        role = "member"
        if user.id == message.guild.owner_id:
            role = "owner"
        elif user.guild_permissions.administrator:
            role = "admin"
        elif user.guild_permissions.manage_messages:
            role = "moderator"
        elif user.bot:
            role = "bot"
        
        data = {
            "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
            "messageId": str(message.id),
            "channelId": str(message.channel.id),
            "channelName": message.channel.name,
            "guildId": str(message.guild.id),
            "guildName": message.guild.name,
            "content": message.content,
            "contentLength": len(message.content),
            "user": {
                "id": str(user.id),
                "username": user.name,
                "discriminator": user.discriminator if user.discriminator != "0" else "",
                "globalName": user.global_name,
                "avatar": str(user.display_avatar.url),
                "isBot": user.bot,
                "role": role,
                "joinedAt": user.joined_at.isoformat() if user.joined_at else None,
                "createdAt": user.created_at.isoformat()
            }
        }
        
        try:
            await message.delete()
        except:
            pass
        
        await send_to_dashboard(data)
        await send_dm_report(message, role)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def monitor(ctx):
    if ctx.channel.id in MONITORED_CHANNELS:
        MONITORED_CHANNELS.remove(ctx.channel.id)
        await ctx.send(f"❌ Stopped monitoring **#{ctx.channel.name}**")
    else:
        MONITORED_CHANNELS.append(ctx.channel.id)
        await ctx.send(f"✅ Now monitoring **#{ctx.channel.name}**!")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

if __name__ == '__main__':
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("Waiting for BOT_TOKEN...")
