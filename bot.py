import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import os
import asyncio
import json
import uuid
from datetime import datetime, timedelta

# -----------------------------
# CARGAR VARIABLES DEL ENTORNO
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))  # Asegúrate de configurar esto en Koyeb

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD = discord.Object(id=GUILD_ID)

EVENTS_FILE = "eventos.json"

# -----------------------------
# BOTONES CON EMOJIS
# -----------------------------
BUTTONS = {
    'INF': ('🪖', discord.ButtonStyle.success),
    'OFICIAL': ('🎖️', discord.ButtonStyle.primary),
    'TANQUE': ('🛡️', discord.ButtonStyle.success),
    'RECON': ('🔭', discord.ButtonStyle.secondary),
    'COMANDANTE': ('⭐', discord.ButtonStyle.danger),
    'DECLINADO': ('❌', discord.ButtonStyle.secondary),
    'TENTATIVO': ('⚠️', discord.ButtonStyle.primary)
}

# -----------------------------
# CARGAR / GUARDAR EVENTOS
# -----------------------------
def load_events():
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_events(events):
    with open(EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=4, default=str)

events = load_events()

# -----------------------------
# FUNCIONES DE ESPERA POR MENSAJE
# -----------------------------
async def wait_for_number(user, dm, min_val, max_val, cancel_word="cancelar"):
    def check(m):
        return m.author == user and m.guild is None
    while True:
        msg = await bot.wait_for("message", check=check)
        if msg.content.lower() == cancel_word:
            return None
        if msg.content.isdigit() and min_val <= int(msg.content) <= max_val:
            return int(msg.content)
        await dm.send(f"Introduce un número entre {min_val} y {max_val}, o '{cancel_word}' para salir.")

async def wait_for_text(user, dm, max_length, allow_none=False, cancel_word="cancelar"):
    def check(m):
        return m.author == user and m.guild is None
    while True:
        msg = await bot.wait_for("message", check=check)
        if msg.content.lower() == cancel_word:
            return None
        if allow_none and msg.content.lower() == "none":
            return ""
        if len(msg.content) <= max_length:
            return msg.content
        await dm.send(f"Texto demasiado largo. Máximo {max_length} caracteres. Escribe '{cancel_word}' para salir.")

# -----------------------------
# CREAR EMBED DE EVENTO
# -----------------------------
def create_event_embed(event):
    embed = discord.Embed(
        title=event["title"],
        description=event["description"] or "Sin descripción",
        color=discord.Color(event.get("color", 0x00ff00))
    )
    embed.add_field(name="Canal", value=f"<#{event['channel_id']}>", inline=False)
    embed.add_field(name="Inicio", value=event["start"], inline=True)
    embed.add_field(name="Duración / Fin", value=event.get("end") or "No especificado", inline=True)

    # Participantes por rol
    for key, (emoji, _) in BUTTONS.items():
        names = event.get("participants_roles", {}).get(key, [])
        text = ", ".join(names) if names else "Nadie aún"
        embed.add_field(name=f"{emoji} {key}", value=text, inline=False)

    # Mostrar roles mencionados
    if event.get("mention_roles"):
        mentions = " ".join(f"<@&{role_id}>" for role_id in event["mention_roles"])
        embed.add_field(name="Roles mencionados", value=mentions, inline=False)

    if event.get("image"):
        embed.set_image(url=event["image"])
    return embed

# -----------------------------
# BOTONES DE INSCRIPCIÓN
# -----------------------------
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
                if "participants_roles" not in event:
                    event["participants_roles"] = {key: [] for key in BUTTONS.keys()}

                if nickname not in event["participants_roles"][self.role_key]:
                    event["participants_roles"][self.role_key].append(nickname)
                    for key, lst in event["participants_roles"].items():
                        if key != self.role_key and nickname in lst:
                            lst.remove(nickname)
                    save_events(events)

                embed = create_event_embed(event)
                channel = bot.get_channel(event["channel_id"])
                if channel and "message_id" in event:
                    try:
                        msg = await channel.fetch_message(event["message_id"])
                        await msg.edit(embed=embed, view=EventView(self.event_id, event["creator_id"]))
                    except:
                        pass

                await interaction.response.send_message(f"Te has inscrito como {self.role_key}", ephemeral=True)
                return

class EventActionButton(discord.ui.Button):
    def __init__(self, label, style, event_id, creator_id):
        super().__init__(label=label, style=style)
        self.event_id = event_id
        self.creator_id = creator_id

    async def callback(self, interaction: discord.Interaction):
        global events
        event = next((e for e in events if e["id"] == self.event_id), None)
        if not event:
            await interaction.response.send_message("Evento no encontrado.", ephemeral=True)
            return
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("Solo el creador del evento puede usar este botón.", ephemeral=True)
            return

        if self.label == "Eliminar evento":
            events.remove(event)
            save_events(events)
            channel = bot.get_channel(event["channel_id"])
            if channel and "message_id" in event:
                try:
                    msg = await channel.fetch_message(event["message_id"])
                    await msg.delete()
                except:
                    pass
            await interaction.response.send_message("Evento eliminado ✅", ephemeral=True)

        elif self.label == "Editar evento":
            await interaction.response.send_message("Funcionalidad de edición aún no implementada en este ejemplo.", ephemeral=True)

class EventView(discord.ui.View):
    def __init__(self, event_id, creator_id):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.creator_id = creator_id
        for role_key, (emoji, style) in BUTTONS.items():
            self.add_item(EventButton(label=role_key, emoji=emoji, style=style, event_id=event_id, role_key=role_key))
        self.add_item(EventActionButton("Editar evento", discord.ButtonStyle.primary, event_id, creator_id))
        self.add_item(EventActionButton("Eliminar evento", discord.ButtonStyle.danger, event_id, creator_id))

# -----------------------------
# TAREA DE RECORDATORIOS
# -----------------------------
@tasks.loop(seconds=60)
async def check_events():
    global events
    now = datetime.now()
    for event in events:
        start_dt = datetime.strptime(event["start"], "%Y-%m-%d %H:%M")
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            continue

        if not event.get("reminder_sent") and start_dt - timedelta(minutes=15) <= now < start_dt:
            mentions = []
            for role in ["INF", "OFICIAL", "TANQUE", "RECON", "COMANDANTE"]:
                for name in event["participants_roles"].get(role, []):
                    member = discord.utils.find(lambda m: m.display_name == name, guild.members)
                    if member:
                        mentions.append(member.mention)
            channel = bot.get_channel(event["channel_id"])
            if channel:
                await channel.send(f"Recordatorio! 15 minutos para el inicio del evento.\nParticipantes: {', '.join(mentions) if mentions else 'Nadie registrado aún.'}")
            event["reminder_sent"] = True
            save_events(events)

# -----------------------------
# COMANDO /eventos
# -----------------------------
@bot.tree.command(name="eventos", description="Crear un evento paso a paso", guild=GUILD)
async def eventos(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Te enviaré un DM para crear el evento paso a paso.", ephemeral=True)
    
    user = interaction.user
    dm = await user.create_dm()

    event = {}
    guild = bot.get_guild(GUILD_ID)
    text_channels = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
    roles = [r for r in guild.roles if not r.is_default() and not r.managed]

    # 1️⃣ Canal
    await dm.send("Selecciona el canal para publicar el evento escribiendo el número:\n" +
                  "\n".join(f"{i+1}. {c.name}" for i, c in enumerate(text_channels)))
    chan_option = await wait_for_number(user, dm, 1, len(text_channels))
    if chan_option is None:
        await dm.send("Creación cancelada.")
        return
    event["channel_id"] = text_channels[chan_option-1].id

    # 2️⃣ Título
    await dm.send("Ingresa el título del evento (máx 200 caracteres):")
    title = await wait_for_text(user, dm, 200)
    if title is None:
        await dm.send("Creación cancelada.")
        return
    event["title"] = title

    # 3️⃣ Descripción
    await dm.send("Ingresa la descripción del evento (máx 1600 caracteres, 'None' para sin descripción):")
    description = await wait_for_text(user, dm, 1600, allow_none=True)
    if description is None:
        await dm.send("Creación cancelada.")
        return
    event["description"] = description or "Sin descripción"

    # 4️⃣ Máximo asistentes
    await dm.send("Número máximo de asistentes (1-250, 'None' para sin límite):")
    while True:
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.guild is None)
        if msg.content.lower() == "cancelar":
            await dm.send("Creación cancelada.")
            return
        if msg.content.lower() == "none":
            event["max_attendees"] = None
            break
        if msg.content.isdigit() and 1 <= int(msg.content) <= 250:
            event["max_attendees"] = int(msg.content)
            break
        await dm.send("Número inválido. Intenta de nuevo.")

    # 5️⃣ Fecha inicio
    await dm.send("Fecha y hora de inicio ('YYYY-MM-DD HH:MM') o 'ahora':")
    while True:
        msg_time = await bot.wait_for("message", check=lambda m: m.author == user and m.guild is None)
        if msg_time.content.lower() == "cancelar":
            await dm.send("Creación cancelada.")
            return
        try:
            start_dt = datetime.now() if msg_time.content.lower() == "ahora" else datetime.strptime(msg_time.content, "%Y-%m-%d %H:%M")
            event["start"] = start_dt.strftime("%Y-%m-%d %H:%M")
            break
        except:
            await dm.send("Formato inválido. Intenta de nuevo.")

    # 6️⃣ Duración
    await dm.send("Duración del evento (ej. '2 horas', '30 minutos', 'None'):")
    duration = await wait_for_text(user, dm, 100, allow_none=True)
    event["end"] = duration or "No especificada"

    # 7️⃣ Opciones avanzadas
    while True:
        await dm.send(
            "Opciones avanzadas:\n"
            "1️⃣ Mencionar roles\n"
            "2️⃣ Añadir imagen\n"
            "3️⃣ Cambiar color\n"
            "4️⃣ Restringir registro a ciertos roles\n"
            "5️⃣ Permitir múltiples respuestas\n"
            "6️⃣ Asignar rol automáticamente\n"
            "7️⃣ Configurar cierre de inscripciones\n"
            "8️⃣ Finalizar creación\n"
            "Escribe el número de la opción:"
        )
        option = await wait_for_number(user, dm, 1, 8)
        if option is None:
            await dm.send("Creación cancelada.")
            return

        if option == 1:
            if not roles:
                await dm.send("No hay roles disponibles.")
                continue
            roles_text = "\n".join(f"{i+1}. {r.name}" for i, r in enumerate(roles))
            await dm.send("Selecciona roles a mencionar (números separados por coma) o 'none':\n" + roles_text)
            response = await wait_for_text(user, dm, 200)
            if response.lower() == "none":
                event["mention_roles"] = []
            else:
                indices = [int(x.strip()) - 1 for x in response.split(",")]
                event["mention_roles"] = [roles[i].id for i in indices if 0 <= i < len(roles)]

        elif option == 2:
            await dm.send("Envía imagen o URL, o 'none':")
            def check_img(m):
                return m.author == user and m.guild is None and (m.attachments or m.content)
            msg_img = await bot.wait_for("message", check=check_img)
            if msg_img.content.lower() == "none":
                continue
            if msg_img.attachments:
                event["image"] = msg_img.attachments[0].url
            else:
                event["image"] = msg_img.content

        elif option == 3:
            await dm.send("Escribe color hexadecimal (ej. FF0000) o 'skip':")
            color_hex = await wait_for_text(user, dm, 7, allow_none=True)
            if color_hex.lower() != "skip":
                event["color"] = int(color_hex.replace("#", ""), 16)

        elif option == 8:
            break  # Finalizar creación

    # Guardar evento
    event["id"] = str(uuid.uuid4())
    event["creator_id"] = user.id
    event["participants_roles"] = {key: [] for key in BUTTONS.keys()}
    event["registration_open"] = True
    event["reminder_sent"] = False
    event["channel_created"] = False

    events.append(event)
    save_events(events)

    # Enviar embed
    channel = bot.get_channel(event["channel_id"])
    if channel:
        embed = create_event_embed(event)
        sent_msg = await channel.send(embed=embed, view=EventView(event["id"], user.id))
        event["message_id"] = sent_msg.id
        save_events(events)
        await dm.send(f"Evento creado correctamente en <#{channel.id}>")
    else:
        await dm.send("No se pudo enviar el evento al canal, pero se guardó en la base de datos.")

# -----------------------------
# COMANDO /proximos_eventos_visual
# -----------------------------
@bot.tree.command(name="proximos_eventos_visual", description="Muestra los próximos eventos tipo calendario con emojis", guild=GUILD)
async def proximos_eventos_visual(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    now = datetime.now()
    global events

    # Filtrar eventos futuros
    upcoming = [e for e in events if datetime.strptime(e["start"], "%Y-%m-%d %H:%M") >= now]
    if not upcoming:
        await interaction.followup.send("No hay eventos próximos.", ephemeral=True)
        return

    # Ordenar por fecha
    upcoming.sort(key=lambda e: datetime.strptime(e["start"], "%Y-%m-%d %H:%M"))

    # Agrupar eventos por día
    events_by_day = {}
    for e in upcoming:
        start_dt = datetime.strptime(e["start"], "%Y-%m-%d %H:%M")
        day_str = start_dt.strftime("%A, %d %B %Y")  # Ej. Lunes, 15 Septiembre 2025
        if day_str not in events_by_day:
            events_by_day[day_str] = []
        events_by_day[day_str].append(e)

    # Crear embed principal
    embed = discord.Embed(
        title="📅 Próximos eventos",
        description="Eventos próximos organizados por día 🌟",
        color=discord.Color.green()
    )

    for day_index, (day, day_events) in enumerate(events_by_day.items()):
        value_text = ""
        for e in day_events:
            start_dt = datetime.strptime(e["start"], "%Y-%m-%d %H:%M")
            time_str = start_dt.strftime("%H:%M")

            # Emojis según proximidad
            delta = start_dt - now
            if delta.total_seconds() < 3600:  # Menos de 1h
                emoji = "🔥"
            elif delta.total_seconds() < 86400:  # Menos de 24h
                emoji = "⏰"
            else:
                emoji = "📌"

            # Añadir detalles del evento
            value_text += f"{emoji} {time_str} - **{e['title']}** en <#{e['channel_id']}>\n"

        # Separador de semanas cada 7 días
        week_emoji = "🗓️" if day_index % 7 == 0 else ""
        embed.add_field(name=f"{week_emoji} {day}", value=value_text, inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

# -----------------------------
# INICIAR BOT
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD)
    check_events.start()
    print(f"Bot conectado como {bot.user}")

bot.run(TOKEN)
