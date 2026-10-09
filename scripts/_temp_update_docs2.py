import os

# Actualizar Índice Principal.md
f = os.path.join("Jarvis", "Índice Principal.md")
with open(f, "rb") as fh:
    raw = fh.read()
t = raw.decode("utf-8", errors="replace").rstrip("\n")

new_entry = "\n- [[Jarvis/resolucion_definitiva_webhook_y_resolver_llamada_segura.md|Resolución Definitiva Webhook y resolver_llamada_segura 2026-10-09]] - Wrapper universal async/sync y notificación de errores en Telegram."

t += new_entry + "\n"

with open(f, "w", encoding="utf-8") as fh:
    fh.write(t)
print("Índice Principal.md actualizado")

# Actualizar estado_proyecto.md
f2 = os.path.join("Jarvis", "estado_proyecto.md")
with open(f2, "rb") as fh:
    raw = fh.read()
t2 = raw.decode("utf-8", errors="replace").rstrip("\n")

new_entry2 = """

- **2026-10-09:** Implementada la función `resolver_llamada_segura()` en `app/routes/telegram.py` para erradicar las excepciones de await en funciones síncronas. Creado `scripts/register_telegram_webhook.py` para re-vincular la URL oficial en Telegram API. Notificación de errores al usuario en Telegram implementada. Pruebas locales al 100%. [[FastAPI]] [[Vercel]] [[Telegram]] [[Python]]"""

t2 += new_entry2 + "\n"

with open(f2, "w", encoding="utf-8") as fh:
    fh.write(t2)
print("estado_proyecto.md actualizado")