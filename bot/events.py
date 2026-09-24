"""bot/events.py - Eventos principales del bot Discord JARVIS.

Este archivo ahora delega la lógica de procesamiento a módulos especializados:
- message_handler: Lógica principal de mensajes
- context_builder: Construcción de contexto para Gemini
- media_processor: Procesamiento de archivos adjuntos
- tts_handler: Manejo de Text-to-Speech
"""
from bot import bot
from bot.events.message_handler import handle_message


@bot.event
async def on_ready():
    """Evento de conexión inicial del bot."""
    print("==================================================")
    print("Sistemas en línea. JARVIS v3.0 Operativo.")
    print(f"Conectado como: {bot.user}")
    print(f"Intents activos: {bot.intents}")
    print("==================================================")


@bot.event
async def on_message(message):
    """Handler principal de mensajes entrantes."""
    print(f"🔥 [ENTRADA DISCORD] Autor: {message.author} | Canal: {message.channel} | Texto: '{message.content}' | Adjuntos: {len(message.attachments)}")
    from bot import bot
    await bot.process_commands(message)
    await handle_message(message)
