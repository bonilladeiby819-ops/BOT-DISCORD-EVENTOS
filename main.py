# main.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# -----------------------------
# CARGAR VARIABLES DE ENTORNO
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

# -----------------------------
# CONFIGURACIÓN DEL BOT
# -----------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# EVENTO ON_READY
# -----------------------------
@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"📌 Slash commands sincronizados en {GUILD_ID}: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"❌ Error al sincronizar: {e}")

    print(f"✅ Bot conectado como {bot.user}")

# -----------------------------
# COMANDO /ping
# -----------------------------
@bot.tree.command(name="ping", description="Responde con Pong!", guild=discord.Object(id=GUILD_ID))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)

# -----------------------------
# COMANDO /hola
# -----------------------------
@bot.tree.command(name="hola", description="Te saluda el bot", guild=discord.Object(id=GUILD_ID))
async def hola(interaction: discord.Interaction):
    await interaction.response.send_message("👋 Hola! ¿Cómo estás?", ephemeral=True)

# -----------------------------
# KEEP ALIVE PARA KOYEB
# -----------------------------
from keep_alive import keep_alive
keep_alive()

# -----------------------------
# INICIAR BOT
# -----------------------------
bot.run(TOKEN)
