import discord
from discord.ext import commands
import asyncio
import uuid
import json
from datetime import datetime
import os

# ------------------ VARIABLES GLOBALES ------------------
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD = discord.Object(id=GUILD_ID)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

EVENTS_FILE = "eventos.json"

BUTTONS = {
    'INF': ('🪖', discord.ButtonStyle.success),
    'OFICIAL': ('🎖️', discord.ButtonStyle.primary),
    'TANQUE': ('🛡️', discord.ButtonStyle.success),
    'RECON': ('🔭', discord.ButtonStyle.secondary),
    'COMANDANTE': ('⭐', discord.ButtonStyle.danger),
}

# ------------------ FUNCIONES PARA EVENTOS ------------------
def load_events():
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_events(events):
    with open(EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=4, default=str)

events = load_events()

def create_event_embed(event):
    embed = discord.Embed(
        title=event["title"],
        description=event.get("description", "Sin descripción"),
        color=discord.Color.green()
    )
    embed.add_field(name="Inicio", value=event["start"], inline=True)
    for key, (emoji, _) in BUTTONS.items():
        names = event.get("participants_roles", {}).get(key, [])
        embed.add_field(name=f"{emoji} {key}", value=", ".join(names) if names else "Nadie", inline=False)
    return embed

class EventButton(discord.ui.Button):
    def __init__(self, label, emoji, style, event_id, role_key):
        super().__init__(label=label, emoji=emoji, style=style)
        self.event_id = event_id
        self.role_key = role_key

    async def callback(self, interaction: discord.Interaction):
        global events
        nickname = interaction.user.display_name
        for event in events:
            if event["id"] == self.event_id:
                if nickname not in event["participants_roles"][self.role_key]:
                    event["participants_roles"][self.role_key].append(nickname)
                    save_events(events)
                embed = create_event_embed(event)
                channel = bot.get_channel(event["channel_id"])
                if channel and "message_id" in event:
                    try:
                        msg = await channel.fetch_message(event["message_id"])
                        await msg.edit(embed=embed, view=EventView(self.event_id))
                    except:
                        pass
                await interaction.response.send_message(f"Te inscribiste como {self.role_key}", ephemeral=True)

class EventView(discord.ui.View):
    def __init__(self, event_id):
        super().__init__(timeout=None)
        for role_key, (emoji, style) in BUTTONS.items():
            self.add_item(EventButton(label=role_key, emoji=emoji, style=style, event_id=event_id, role_key=role_key))

# ------------------ FLUJO DE CREACIÓN EN DM ------------------
async def handle_event_creation(user, channel_id):
    dm = await user.create_dm()

    await dm.send("🎉 Vamos a crear un evento. Escribe el título:")
    def check(m): return m.author == user and m.guild is None
    msg = await bot.wait_for("message", check=check)
    title = msg.content

    await dm.send("📅 Escribe la fecha y hora de inicio en formato `YYYY-MM-DD HH:MM`:")
    while True:
        msg = await bot.wait_for("message", check=check)
        try:
            start_dt = datetime.strptime(msg.content, "%Y-%m-%d %H:%M")
            start = start_dt.strftime("%Y-%m-%d %H:%M")
            break
        except:
            await dm.send("Formato inválido. Intenta otra vez (ejemplo: 2025-09-16 20:30).")

    # Crear el evento
    event = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": "Evento creado desde DM",
        "start": start,
        "channel_id": channel_id,
        "participants_roles": {k: [] for k in BUTTONS.keys()}
    }

    events.append(event)
    save_events(events)

    # Publicar en canal
    channel = bot.get_channel(channel_id)
    if channel:
        embed = create_event_embed(event)
        sent_msg = await channel.send(embed=embed, view=EventView(event["id"]))
        event["message_id"] = sent_msg.id
        save_events(events)
        await dm.send(f"✅ Evento creado en {channel.mention}")
    else:
        await dm.send("⚠️ No se encontró el canal.")

# ------------------ COMANDOS SLASH ------------------
@bot.tree.command(name="eventos", description="Crear un evento paso a paso", guild=GUILD)
async def eventos(interaction: discord.Interaction):
    # 🔹 Responder rápido para evitar "Aplicación no ha respondido"
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("📩 Te envié un DM para crear el evento.", ephemeral=True)

    # 🔹 Iniciar el flujo en segundo plano
    asyncio.create_task(handle_event_creation(interaction.user, interaction.channel_id))

@bot.tree.command(name="proximos_eventos_visual", description="Muestra todos los próximos eventos", guild=GUILD)
async def proximos_eventos_visual(interaction: discord.Interaction):
    if not events:
        await interaction.response.send_message("❌ No hay eventos registrados.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)
    for event in events:
        embed = create_event_embed(event)
        await interaction.followup.send(embed=embed, view=EventView(event["id"]))

# ------------------ READY ------------------
@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD)
    print(f"✅ Bot conectado como {bot.user}")

bot.run(TOKEN)
