# Monitoreo de Salud de la API con UptimeRobot

**Propósito**: Mantener la función Serverless en Vercel libre de Cold Starts prolongados y monitorear la disponibilidad de la API.

**Configuración**:
- URL del Monitor: `https://jarvis.vercel.app/api/widget/dashboard`
- Tipo de Monitor: HTTP(s)
- Intervalo de Chequeo: Cada 5 minutos (previene Cold Starts en Vercel Serverless).
- Palabras Clave de Validación (Opcional): `"accounts"` o `"nu"`.

**Enlaces Wiki**:
- [[Jarvis/estado_proyecto.md]]
- [[Jarvis/Vercel.md]]
- [[Jarvis/Índice Principal.md]]
- [[Jarvis/migracion_render_a_vercel.md]] - Guía de migración de Render a Vercel.