# Fix: Error 404 en todos los endpoints Vercel

**Fecha:** 2026-10-10  
**Estado:** ✅ Resuelto

## Problema

Todos los endpoints de la API retornaban HTTP 404 en producción (Vercel), incluyendo `/api/telegram/health`, `/api/telegram/webhook`, y el spec OpenAPI (`/openapi.json`).

## Diagnóstico

Se identificaron dos causas raíz:

### 1. Duplicidad de prefijo en Telegram Router

`app/routes/telegram.py` tenía `APIRouter(prefix="/api/telegram")` y `app/main.py` hacía `include_router(telegram_router, prefix="/api/telegram")`. Esto generaba rutas duplicadas como `/api/telegram/api/telegram/health`.

**Fix:** Se eliminó `prefix="/api/telegram"` de `APIRouter()` en `telegram.py`, manteniéndolo solo en `include_router()` de `main.py`.

### 2. Rewrite incorrecto en vercel.json

La configuración de rewrites hacia `app/main.py` causaba conflictos con el framework auto-detectado de Vercel (FastAPI).

**Fix:** Se removió el bloque `rewrites` de `vercel.json`, permitiendo que Vercel use su auto-detección de FastAPI.

## Cambios realizados

| Archivo | Cambio |
|---------|--------|
| `app/routes/telegram.py` | Eliminado `prefix="/api/telegram"` del `APIRouter()` |
| `app/main.py` | Eliminado health endpoint duplicado (comentado) |
| `vercel.json` | Eliminada sección `rewrites`, mantenido solo `env` |
| `server.py` | Creado como entry point para Vercel Python Serverless |

## Verificación

Post-fix, todos los endpoints respondieron correctamente:

```bash
GET /api/telegram/health    → 200 {"status":"ok",...}
GET /api/telegram/set-webhook → 200 {"ok":true,"result":true}
GET /openapi.json           → 200 {"openapi":"3.1.0",...}
GET /docs                   → 200 (Swagger UI)
```

## Commits

- `218dc61` fix(routes): eliminar prefijo duplicado en telegram router y health endpoint
- `01aec5a` chore: crear server.py como entry point para Vercel Python
- `d13aaaa` fix(vercel): quitar rewrite para usar auto-detección de framework

## Referencias

- [[Vercel]]
- [[FastAPI]]
- [[Jarvis/telegram_bot_webhook.md]]
