import os

f = os.path.join("Jarvis", "Índice Principal.md")
with open(f, "rb") as fh:
    raw = fh.read()
t = raw.decode("utf-8", errors="replace").rstrip("\n")

new_entry = "\n- [[Jarvis/resolucion_definitiva_webhook_y_resolver_llamada_segura.md|Resolución Definitiva Webhook y resolver_llamada_segura 2026-10-09]] - Wrapper universal async/sync y notificación de errores en Telegram."

t += new_entry + "\n"

with open(f, "w", encoding="utf-8") as fh:
    fh.write(t)
print("Índice Principal.md actualizado")