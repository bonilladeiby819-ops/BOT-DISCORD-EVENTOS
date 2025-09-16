from keep_alive import keep_alive
import os
import discord
from discord.ext import commands

# ==============================
# CONFIGURACIÓN
# ==============================
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
GUILD = discord.Object(id=GUILD_ID)

# Intents necesarios
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

# Usamos commands.Bot (NO Client)
bot = commands.Bot(command_prefix="!", intents=intents)


# ==============================
# EVENTO ON_READY
# ==============================
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync(guild=GUILD)
        print(f"📌 {len(synced)} comandos sincronizados en {GUILD_ID}")
    except Exception as e:
        print(f"❌ Error al sincronizar: {e}")


# ==============================
# COMANDOS
# ==============================

# /ping
@bot.tree.command(name="ping", description="Responde con Pong!", guild=GUILD)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")


# /eventos
@bot.tree.command(name="eventos", description="Crear un evento paso a paso", guild=GUILD)
async def eventos(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🎉 Aquí empezaría el proceso de creación del evento..."
    )


# ==============================
# KEEP ALIVE + RUN
# ==============================
keep_alive()
bot.run(TOKEN)



