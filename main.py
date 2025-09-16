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
# FUNCIONES AUXILIARES PARA INTERACCIÓN POR DM
# -----------------------------
async def wait_for_number(user, dm, min_val, max_val, timeout=60):
    """Espera a que el usuario envíe un número entre min_val y max_val"""
    try:
        msg = await bot.wait_for(
            "message",
            timeout=timeout,
            check=lambda m: m.author == user and m.guild is None
        )
        if msg.content.lower() == "cancelar":
            return None
        if msg.content.isdigit():
            num = int(msg.content)
            if min_val <= num <= max_val:
                return num
        await dm.send(f"Número inválido. Debe ser entre {min_val} y {max_val}.")
        return await wait_for_number(user, dm, min_val, max_val, timeout)
    except:
        return None

async def wait_for_text(user, dm, max_len, allow_none=False, timeout=120):
    """Espera a que el usuario envíe un texto de hasta max_len caracteres"""
    try:
        msg = await bot.wait_for(
            "message",
            timeout=timeout,
            check=lambda m: m.author == user and m.guild is None
        )
        if msg.content.lower() == "cancelar":
            return None
        if allow_none and msg.content.lower() == "none":
            return None
        if len(msg.content) <= max_len:
            return msg.content
        await dm.send(f"Texto demasiado largo, máximo {max_len} caracteres.")
        return await wait_for_text(user, dm, max_len, allow_none, timeout)
    except:
        return None

# -----------------------------
# COMANDO /eventos
# -----------------------------
@bot.tree.command(name="eventos", description="Crear un evento paso a paso", guild=discord.Object(id=GUILD_ID))
async def eventos(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # Dice a Discord "espera"
    await interaction.followup.send("Te enviaré un DM para crear el evento paso a paso.", ephemeral=True)
    user = interaction.user
    dm = await user.create_dm()

    event = {}  # Diccionario temporal

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
    # 7️⃣ OPCIONES AVANZADAS
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

    # -----------------------------
    # Enviar embed con roles mencionados
    # -----------------------------
    channel = bot.get_channel(event["channel_id"])
    if channel:
        embed = create_event_embed(event)
        sent_message = await channel.send(embed=embed, view=EventView(event_id, user.id))
        event["message_id"] = sent_message.id
        save_events(events)
        await dm.send(f"Evento creado correctamente en <#{channel.id}>")
    else:
        await dm.send("No se pudo enviar el evento al canal, pero se guardó en la base de datos.")

# -----------------------------
# COMANDO /proximos_eventos_visual
# -----------------------------
@bot.tree.command(name="proximos_eventos_visual", description="Muestra los próximos eventos tipo calendario con emojis", guild=discord.Object(id=GUILD_ID))
async def proximos_eventos_visual(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    global events
    now = datetime.now()

    # Filtrar eventos futuros
    upcoming = [e for e in events if datetime.strptime(e["start"], "%Y-%m-%d %H:%M") >= now]

    if not upcoming:
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # Ordenar por fecha
    upcoming.sort(key=lambda e: datetime.strptime(e["start"], "%Y-%m-%d %H:%M"))

    # Agrupar por día
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

    await interaction.response.send_message(embed=embed)


# -----------------------------
# KEEP ALIVE PARA KOYEB
# -----------------------------
from keep_alive import keep_alive
keep_alive()

# -----------------------------
# INICIAR BOT
# -----------------------------
bot.run(TOKEN)
