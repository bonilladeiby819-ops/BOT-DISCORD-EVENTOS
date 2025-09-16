from keep_alive import keep_alive
import os
import discord
from discord.ext import commands
import asyncio
import uuid
from datetime import datetime, timedelta

# ------------------------
# CONFIGURACIÓN
# ------------------------
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])  # asegúrate de ponerlo bien en Koyeb

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
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"🔄 {len(synced)} comandos sincronizados en {GUILD_ID}")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

# ------------------------
# COMANDO PING
# ------------------------
@bot.tree.command(name="ping", description="Prueba si el bot responde", guild=discord.Object(id=int(os.environ["GUILD_ID"])))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! El bot está activo.", ephemeral=True)

# ------------------------
# COMANDO EVENTOS
# ------------------------
@bot.tree.command(name="eventos", description="Crear un evento paso a paso", guild=discord.Object(id=int(os.environ["GUILD_ID"])))
async def eventos(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("📩 Te enviaré un DM para crear el evento paso a paso.", ephemeral=True)

    # Llamamos la creación en segundo plano
    asyncio.create_task(handle_event_creation(interaction.user))

async def handle_event_creation(user: discord.User):
    try:
        dm = await user.create_dm()
        await dm.send("👋 Hola! Vamos a crear tu evento.")
        
        # Preguntar nombre
        await dm.send("✍️ Escribe el **nombre del evento**:")
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == dm, timeout=120)
        event_name = msg.content

        # Preguntar fecha
        await dm.send("📅 Escribe la **fecha del evento** (formato: YYYY-MM-DD HH:MM):")
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.channel == dm, timeout=120)
        try:
            event_date = datetime.strptime(msg.content, "%Y-%m-%d %H:%M")
        except ValueError:
            await dm.send("❌ Formato de fecha inválido. Evento cancelado.")
            return

        # Crear ID único
        event_id = str(uuid.uuid4())[:8]

        # Confirmar
        await dm.send(f"✅ Evento creado:\n**{event_name}**\n📅 {event_date}\n🆔 ID: `{event_id}`")

    except asyncio.TimeoutError:
        await user.send("⌛ Se agotó el tiempo. Intenta crear el evento de nuevo.")
    except Exception as e:
        print(f"❌ Error en creación de evento: {e}")
        try:
            await user.send("❌ Hubo un error al crear el evento.")
        except:
            pass

# ------------------------
# KEEP ALIVE + RUN
# ------------------------
keep_alive()
bot.run(TOKEN)


