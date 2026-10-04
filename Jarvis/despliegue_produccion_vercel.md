# 🚀 Despliegue en Producción — Vercel

> Nota de verificación E2E del sistema JARVIS desplegado en Vercel (serverless).

---

## 📋 Resumen del Despliegue

| Ítem | Valor |
|------|-------|
| **Plataforma** | [[Vercel]] |
| **URL de producción** | `https://jarvis.vercel.app` |
| **Entrypoint** | `app/main.py` |
| **Runtime** | Python 3.11 |
| **Framework** | [[FastAPI]] |
| **Fecha de verificación** | 2026-10-04 |

---

## 🔧 Configuración `vercel.json`

La configuración migró del formato legacy `builds` + `routes` (que generaba warnings de *Build Settings*) al formato moderno con `functions` + `rewrites`:

```json
{
    "version": 2,
    "functions": {
        "app/main.py": {
            "runtime": "python3.11"
        }
    },
    "rewrites": [
        {
            "source": "/(.*)",
            "destination": "app/main.py"
        }
    ]
}
```

**Por qué `rewrites` en lugar de `routes`:**
- `routes` (legacy) requería reglas explícitas por prefijo (`/api/(.*)` + `/(.*)`) y generaba warnings en el panel de Vercel.
- `rewrites` enruta todo el tráfico a `app/main.py` sin warnings, dejando que [[FastAPI]] gestione internamente el routing mediante sus routers.

---

## 🗺️ Arquitectura de Routing

```
Cliente (iPhone/Telegram)
        │
        ▼
https://jarvis.vercel.app/{cualquier-ruta}
        │
        ▼ (vercel.json rewrites)
app/main.py  ──import──▶  app/routes/__init__.py
                                    │
                        ┌───────────┼───────────┐
                        ▼           ▼           ▼
              widgets.router  telegram.router  (app directo)
              prefix=/api/widget  prefix=/api/telegram
```

### Endpoints principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Health check + estado del servidor |
| `/health` | GET | Keep-Alive para [[Jarvis/monitoreo_uptimerobot.md\|UptimeRobot]] |
| `/api/widget/dashboard` | GET | Datos del widget iPhone (Scriptable) |
| `/api/telegram/webhook` | POST | Recepción de eventos de [[Jarvis/telegram_bot_webhook.md\|Telegram]] |
| `/api/telegram/set-webhook` | GET | Registro del webhook en la API de Telegram |

---

## 📱 Widget iPhone — Verificación Scriptable

El cliente en [[widgets/jarvis_widget.js]] usa:

```javascript
const BASE_URL = "https://jarvis.vercel.app"
const url = `${BASE_URL}/api/widget/dashboard?usuario_id=${USER_ID}`
const data = await fetchJSON(url)
```

**Parseo de respuesta:** El widget valida `if (!data || data.error)` antes de renderizar, mostrando un mensaje de error si la API no responde. El campo `usuario_id` se envía como query param para filtrar datos por usuario.

---

## 🤖 Telegram Webhook — Estado

| Campo | Valor |
|-------|-------|
| **URL anterior (incorrecta)** | `https://jarvis-vy8k.onrender.com/webhook` |
| **URL correcta** | `https://jarvis.vercel.app/api/telegram/webhook` |
| **Estado** | ⚠️ Pendiente actualización post-redeploy |

Para actualizar el webhook tras el redeploy:
```
GET https://jarvis.vercel.app/api/telegram/set-webhook
```

---

## 🔄 Flujo de Redeploy

1. Modificar código localmente
2. `git add . && git commit -m "mensaje" && git push`
3. Vercel detecta el push y redeploy automáticamente (~60s)
4. Verificar en: `https://jarvis.vercel.app/health`

---

## 🐛 Problemas Conocidos y Soluciones

### Error HTTP 404 en todos los endpoints
- **Causa:** Código local sin pushear → Vercel ejecuta versión desactualizada.
- **Solución:** `git push` para triggerear redeploy.
- **Documentado en:** [[Jarvis/vercel_routing_fix.md]]

### Warning "Build Settings" en panel Vercel
- **Causa:** Uso del formato legacy `builds` + `routes` en `vercel.json`.
- **Solución:** Migrar a `functions` + `rewrites` (aplicado en esta sesión).

### Webhook Telegram apuntando a Render
- **Causa:** Configuración residual del servidor anterior en Render.
- **Solución:** Llamar a `/api/telegram/set-webhook` después del redeploy.

---

## 📎 Referencias

- [[Vercel.md]] — Infraestructura serverless general
- [[Jarvis/vercel_routing_fix.md]] — Historial de fix de routing
- [[Jarvis/telegram_bot_webhook.md]] — Configuración del webhook de Telegram
- [[Jarvis/monitoreo_uptimerobot.md]] — Monitoreo de salud con UptimeRobot
- [[FastAPI.md]] — Framework web usado como entrypoint
- [[estado_proyecto.md]] — Bitácora del proyecto
