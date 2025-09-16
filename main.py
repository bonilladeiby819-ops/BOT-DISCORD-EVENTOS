from keep_alive import keep_alive
import os
import discord
from discord.ext import commands

TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])  # 👈 pon tu server ID en Koyeb
GUILD = discord.Object(id=GUILD_ID)

# Configuración de intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD)  # 👈 sincroniza los slash commands en tu server
    print(f"✅ Bot conectado como {bot.user}")
    print(f"📌 Slash commands sincronizados en {GUILD_ID}")

# Slash command de prueba
@bot.tree.command(name="ping", description="Prueba slash command", guild=GUILD)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)

# Inicia el servidor keep-alive
keep_alive()

# Inicia el bot
bot.run(TOKEN)

