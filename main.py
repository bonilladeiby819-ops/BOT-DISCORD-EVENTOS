from keep_alive import keep_alive
import os
import discord

TOKEN = os.environ["DISCORD_TOKEN"]

# Configuración de intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Bot conectado como {client.user}")

# Inicia el servidor keep-alive
keep_alive()

# Inicia el bot
client.run(TOKEN)
