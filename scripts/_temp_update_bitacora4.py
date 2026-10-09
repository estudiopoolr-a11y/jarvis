import os
f = os.path.join("Jarvis", "estado_proyecto.md")
with open(f, "rb") as fh:
    raw = fh.read()
t = raw.decode("utf-8", errors="replace").rstrip("\n")

new_entry = """

- **2026-10-09:** Solucionado error de startup y runtime `ModuleNotFoundError: PIL` en Vercel. Agregada la librería `Pillow` a `requirements.txt` y blindada la importación en `modules/gemini/vision.py`. [[FastAPI]] [[Vercel]] [[Python]] [[Gemini API]] [[Telegram]]"""

t += new_entry + "\n"

with open(f, "w", encoding="utf-8") as fh:
    fh.write(t)
print("Bitácora actualizada")