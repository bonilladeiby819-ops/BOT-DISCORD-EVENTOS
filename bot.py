from keep_alive import keep_alive
import os
import discord
from discord.ext import commands

# ------------------------
# CONFIGURACIÓN
# ------------------------
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])  # Asegúrate que en Koyeb esté bien

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------
# EVENTOS
# ------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        # Sincronizar comandos con el servidor
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"🔄 {len(synced)} comandos sincronizados en el servidor {GUILD_ID}")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

# ------------------------
# COMANDOS
# ------------------------
@bot.tree.command(name="ping", description="Prueba si el bot responde", guild=discord.Object(id=int(os.environ["GUILD_ID"])))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! El bot está activo.", ephemeral=True)

# ------------------------
# KEEP ALIVE + RUN
# ------------------------
keep_alive()
bot.run(TOKEN)

