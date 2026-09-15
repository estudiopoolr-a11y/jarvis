"""Entrypoint del worker Discord de JARVIS."""
from bot import TOKEN, bot, register_handlers

register_handlers()

if __name__ == "__main__" and TOKEN:
    bot.run(TOKEN)
