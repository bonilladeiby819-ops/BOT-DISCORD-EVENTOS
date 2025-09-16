# -----------------------------
# BOT DE EVENTOS - KOYEB
# -----------------------------
import os
import json
import uuid
import asyncio
import discord
from discord.ext import commands
from datetime import datetime
from keep_alive import keep_alive

# -----------------------------
# VARIABLES DE ENTORNO
# -----------------------------
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
GUILD = discord.Object(id=GUILD_ID)

# -----------------------------
# CONFIGURACIÓN DEL BOT
# -----------------------------
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
# -----------------------------
# DATOS DEL EVENTO
# -----------------------------
events = []

BUTTONS = {
    "Tanque": "🛡️",
    "Healer": "💉",
    "DPS": "⚔️",
}

# -----------------------------
# HELPERS
# -----------------------------
async def wait_for_number(user, dm, min_val, max_val):
    while True:
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.guild is None)
        if msg.content.lower() == "cancelar":
            return None
        if msg.content.isdigit() and min_val <= int(msg.content) <= max_val:
            return int(msg.content)
        await dm.send(f"Número inválido, ingresa entre {min_val}-{max_val} o 'cancelar'.")

async def wait_for_text(user, dm, max_len, allow_none=False):
    while True:
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.guild is None)
        if msg.content.lower() == "cancelar":
            return None
        if allow_none and msg.content.lower() == "none":
            return "none"
        if len(msg.content) <= max_len:
            return msg.content
        await dm.send(f"Texto demasiado largo, máximo {max_len} caracteres.")

def save_events(events_list):
    with open("events.json", "w") as f:
        json.dump(events_list, f, indent=4, default=str)

def create_event_embed(event):
    embed = discord.Embed(
        title=event["title"],
        description=event["description"],
        color=event.get("color", 0x00FF00),
        timestamp=datetime.strptime(event["start"], "%Y-%m-%d %H:%M")
    )
    if "image" in event:
        embed.set_image(url=event["image"])
    if event.get("mention_roles"):
        mention_text = " ".join(f"<@&{r_id}>" for r_id in event["mention_roles"])
        embed.description = f"{mention_text}\n{embed.description}"
    return embed

class EventView(discord.ui.View):
    def __init__(self, event_id, creator_id):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.creator_id = creator_id
        for role_name, emoji in BUTTONS.items():
            self.add_item(discord.ui.Button(label=role_name, emoji=emoji, custom_id=role_name))

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

    # -----------------------------
    # 1️⃣ Canal
    # -----------------------------
    await dm.send("¿Dónde publicar el evento?\n1️⃣ Canal actual\n2️⃣ Otro canal\nEscribe el número o 'cancelar'.")
    option = await wait_for_number(user, dm, 1, 2)
    if option is None:
        await dm.send("Creación cancelada.")
        return

    if option == 1:
        channel_id = interaction.channel_id
    else:
        guild = bot.get_guild(GUILD_ID)
        text_channels = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
        await dm.send("Listado de canales:\n" + "\n".join(f"{i+1}. {c.name}" for i, c in enumerate(text_channels)))
        chan_option = await wait_for_number(user, dm, 1, len(text_channels))
        if chan_option is None:
            await dm.send("Creación cancelada.")
            return
        channel_id = text_channels[chan_option - 1].id
    event["channel_id"] = channel_id

    # -----------------------------
    # 2️⃣ Título
    # -----------------------------
    await dm.send("Ingresa el título del evento (máx 200 caracteres):")
    title = await wait_for_text(user, dm, 200)
    if title is None:
        await dm.send("Creación cancelada.")
        return
    event["title"] = title

    # -----------------------------
    # 3️⃣ Descripción
    # -----------------------------
    await dm.send("Ingresa la descripción (máx 1600 caracteres, 'None' para sin descripción):")
    description = await wait_for_text(user, dm, 1600, allow_none=True)
    if description is None:
        await dm.send("Creación cancelada.")
        return
    event["description"] = description or "Sin descripción"

    # -----------------------------
    # 4️⃣ Máximo asistentes
    # -----------------------------
    await dm.send("Número máximo de asistentes (1-250, 'None' para sin límite):")
    while True:
        msg = await bot.wait_for("message", check=lambda m: m.author == user and m.guild is None)
        if msg.content.lower() == "cancelar":
            await dm.send("Creación cancelada.")
            return
        if msg.content.lower() == "none":
            max_attendees = None
            break
        if msg.content.isdigit() and 1 <= int(msg.content) <= 250:
            max_attendees = int(msg.content)
            break
        await dm.send("Número inválido. Intenta de nuevo.")
    event["max_attendees"] = max_attendees

    # -----------------------------
    # 5️⃣ Fecha inicio
    # -----------------------------
    await dm.send("Fecha y hora de inicio ('YYYY-MM-DD HH:MM') o 'ahora':")
    while True:
        msg_time = await bot.wait_for("message", check=lambda m: m.author == user and m.guild is None)
        if msg_time.content.lower() == "cancelar":
            await dm.send("Creación cancelada.")
            return
        try:
            start_dt = datetime.now() if msg_time.content.lower() == "ahora" else datetime.strptime(msg_time.content, "%Y-%m-%d %H:%M")
            break
        except:
            await dm.send("Formato inválido. Intenta de nuevo.")
    event["start"] = start_dt.strftime("%Y-%m-%d %H:%M")

    # -----------------------------
    # 6️⃣ Duración
    # -----------------------------
    await dm.send("Duración del evento (ej. '2 horas', '1 día', '30 minutos') o 'None' si no hay duración:")
    duration = await wait_for_text(user, dm, 100, allow_none=True)
    event["end"] = duration or "No especificada"

    # -----------------------------
    # 7️⃣ Opciones avanzadas
    # -----------------------------
    guild = bot.get_guild(GUILD_ID)
    roles = [r for r in guild.roles if not r.is_default() and not r.managed]

    while True:
        await dm.send(
            "Opciones avanzadas:\n"
            "1️⃣ Mencionar roles al publicar\n"
            "2️⃣ Añadir imagen al embed\n"
            "3️⃣ Cambiar color del evento\n"
            "4️⃣ Restringir registro a ciertos roles\n"
            "5️⃣ Permitir múltiples respuestas por usuario\n"
            "6️⃣ Asignar un rol a los asistentes\n"
            "7️⃣ Configurar cierre de inscripciones\n"
            "8️⃣ Finalizar creación del evento\n"
            "Escribe el número de la opción que quieres configurar, o '8' para finalizar."
        )
        option = await wait_for_number(user, dm, 1, 8)
        if option is None:
            await dm.send("Creación cancelada.")
            return
        # -----------------------------
        # 1️⃣ Mencionar roles
        # -----------------------------
        if option == 1:
            if not roles:
                await dm.send("No hay roles disponibles para mencionar.")
                continue
            roles_text = "\n".join(f"{i+1}. {r.name}" for i, r in enumerate(roles))
            await dm.send("Selecciona los roles a mencionar escribiendo sus números separados por comas, o 'none':\n" + roles_text)
            while True:
                response = await wait_for_text(user, dm, 200)
                if response.lower() == "none":
                    event["mention_roles"] = []
                    break
                try:
                    indices = [int(x.strip()) - 1 for x in response.split(",")]
                    selected_roles = [roles[i].id for i in indices if 0 <= i < len(roles)]
                    if selected_roles:
                        event["mention_roles"] = selected_roles
                        break
                    else:
                        await dm.send("Ningún rol válido seleccionado. Intenta de nuevo o 'none'.")
                except:
                    await dm.send("Entrada inválida. Escribe los números separados por comas o 'none'.")

        # -----------------------------
        # 2️⃣ Añadir imagen
        # -----------------------------
        elif option == 2:
            await dm.send("Envía la imagen directamente al chat o un URL de imagen, o escribe 'none' para omitir:")

            def check_img(m):
                return m.author == user and m.guild is None and (m.attachments or m.content)

            while True:
                msg_img = await bot.wait_for("message", check=check_img)
                if msg_img.content.lower() == "cancelar":
                    await dm.send("Creación cancelada.")
                    return
                if msg_img.content.lower() == "none":
                    break

                # Archivo
                if msg_img.attachments:
                    attachment = msg_img.attachments[0]
                    if attachment.content_type.startswith("image/"):
                        event["image"] = attachment.url
                        await dm.send("Imagen añadida correctamente ✅")
                        break
                    else:
                        await dm.send("El archivo no es una imagen válida. Intenta otra vez.")
                        continue

                # URL
                elif msg_img.content.startswith("http"):
                    event["image"] = msg_img.content
                    await dm.send("Imagen añadida correctamente ✅")
                    break
                else:
                    await dm.send("Debes enviar un URL válido o subir una imagen directamente.")

        # -----------------------------
        # 3️⃣ Color
        # -----------------------------
        elif option == 3:
            await dm.send("Escribe el color en hexadecimal (ej. FF0000) o 'skip' para dejarlo verde:")
            color_hex = await wait_for_text(user, dm, 7, allow_none=True)
            if color_hex.lower() != "skip":
                try:
                    color_str = color_hex.replace("#", "")
                    event["color"] = int(color_str, 16)
                except ValueError:
                    await dm.send("Color inválido, se usará verde por defecto.")

        # -----------------------------
        # 4️⃣ Restringir registro
        # -----------------------------
        elif option == 4:
            if not roles:
                await dm.send("No hay roles disponibles.")
                continue
            roles_text = "\n".join(f"{i+1}. {r.name}" for i, r in enumerate(roles))
            await dm.send("Selecciona los roles permitidos escribiendo sus números separados por comas, o 'none':\n" + roles_text)
            while True:
                response = await wait_for_text(user, dm, 200)
                if response.lower() == "none":
                    event["allowed_roles"] = []
                    break
                try:
                    indices = [int(x.strip()) - 1 for x in response.split(",")]
                    allowed_roles = [roles[i].id for i in indices if 0 <= i < len(roles)]
                    if allowed_roles:
                        event["allowed_roles"] = allowed_roles
                        break
                    else:
                        await dm.send("Ningún rol válido. Intenta de nuevo o escribe 'none'.")
                except:
                    await dm.send("Entrada inválida. Intenta de nuevo.")

        # -----------------------------
        # 5️⃣ Multi-respuesta
        # -----------------------------
        elif option == 5:
            await dm.send("Permitir que un usuario elija múltiples roles? (si/no)")
            multi = await wait_for_text(user, dm, 3)
            event["multi_response"] = True if multi.lower() == "si" else False

        # -----------------------------
        # 6️⃣ Asignar rol automáticamente
        # -----------------------------
        elif option == 6:
            if not roles:
                await dm.send("No hay roles disponibles.")
                continue
            roles_text = "\n".join(f"{i+1}. {r.name}" for i, r in enumerate(roles))
            await dm.send("Selecciona el rol que se asignará automáticamente a los asistentes o 'none':\n" + roles_text)
            while True:
                response = await wait_for_text(user, dm, 100)
                if response.lower() == "none":
                    event["assign_role"] = None
                    break
                try:
                    index = int(response.strip()) - 1
                    if 0 <= index < len(roles):
                        event["assign_role"] = roles[index].id
                        break
                    else:
                        await dm.send("Número inválido. Intenta de nuevo o 'none'.")
                except:
                    await dm.send("Entrada inválida. Intenta de nuevo o 'none'.")
        elif option == 7:  # Cierre de inscripciones
            await dm.send("Escribe cuándo cerrar las inscripciones ('10 minutos', '1 hora', 'none'):")
            close_time = await wait_for_text(user, dm, 50, allow_none=True)
            if close_time.lower() != "none":
                event["registration_close"] = close_time
        elif option == 8:  # Finalizar
            break
            # -----------------------------
    # Guardar evento
    # -----------------------------
    event_id = str(uuid.uuid4())
    event["id"] = event_id
    event["creator_id"] = user.id
    event["participants_roles"] = {key: [] for key in BUTTONS.keys()}
    event["registration_open"] = True
    event["reminder_sent"] = False
    event["channel_created"] = False

    events.append(event)
    save_events(events)

    channel = bot.get_channel(event["channel_id"])
    if channel:
        embed = create_event_embed(event)
        sent_message = await channel.send(embed=embed, view=EventView(event_id, user.id))
        event["message_id"] = sent_message.id
        save_events(events)
        await dm.send(f"Evento creado correctamente en <#{channel.id}>")
    else:
        await dm.send("No se pudo enviar el evento al canal, pero se guardó en la base de datos.")

# ------------------ COMANDO PING ------------------
@bot.tree.command(name="ping", description="Prueba rápida", guild=GUILD)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! El bot está respondiendo correctamente.", ephemeral=True)

# -----------------------------
# ON READY
# -----------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    await bot.tree.sync(guild=GUILD)  # Sincroniza los comandos slash

# -----------------------------
# KEEP ALIVE (Koyeb)
# -----------------------------
keep_alive()

# -----------------------------
# RUN
# -----------------------------
bot.run(TOKEN)

