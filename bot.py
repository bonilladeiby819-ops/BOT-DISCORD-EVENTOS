import discord
from discord.ext import commands
import os

# ------------------ VARIABLES ------------------
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))  # 👈 Muy importante en Koyeb
GUILD = discord.Object(id=GUILD_ID)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ COMANDO PING ------------------
@bot.tree.command(name="ping", description="Prueba rápida", guild=GUILD)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! El bot está respondiendo correctamente.", ephemeral=True)

# ------------------ EVENTO READY ------------------
@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD)  # 👈 Sincroniza comandos slash en tu servidor
    print(f"✅ Bot conectado como {bot.user}")

# ------------------ EJECUTAR BOT ------------------
bot.run(TOKEN)

