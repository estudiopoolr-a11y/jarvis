"""
bot - Núcleo del bot Discord JARVIS.

Este módulo crea la instancia única de Discord. Los handlers se importan
al final para registrar comandos sobre la misma instancia.
"""
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
TEMP_DIR = "temp_audios"
Path(TEMP_DIR).mkdir(exist_ok=True)

# IDs de roles que pueden invocar al bot.
ALLOWED_ROLE_IDS = [1537704466407497738]

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.dm_messages = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


def register_handlers() -> None:
    """Importa eventos y comandos para registrarlos en ``bot``."""
    from bot import events  # noqa: F401
    from bot.handlers import finanzas, tareas, metas, pagos, presupuestos, sistema, mantenimiento  # noqa: F401
