# Corrección de Enrutamiento Serverless en Vercel

**Propósito**: Documentar la causa raíz del error HTTP 404 en el endpoint `/api/widget/dashboard` y la solución aplicada para corregir el enrutamiento serverless en Vercel.

## Causa Raíz del Error 404

El error HTTP 404 al acceder a `https://jarvis.vercel.app/api/widget/dashboard` se debió a dos problemas de configuración:

1. **En `app/routes/widgets.py`**: El endpoint estaba definido con el prefijo completo `/api/widget/dashboard` en el decorador, pero el router no estaba registrado con el prefijo `/api/widget` en la aplicación principal.

2. **En `vercel.json`**: La configuración de rutas solo incluía redirecciones para `/api/telegram/(.*)` y `/*`, pero no para `/api/(.*)`, lo que hacía que las solicitudes a `/api/widget/dashboard` no llegaran a la aplicación FastAPI.

## Solución Aplicada

### 1. Modificación de `app/routes/widgets.py`:
- Cambiar el import para incluir `app` desde `app.api`
- Crear un `APIRouter` separado para los endpoints de widgets
- Cambiar el decorador de `@app.get("/api/widget/dashboard")` a `@router.get("/dashboard")`
- Mantener el router registrado en `app/routes/__init__.py` (ya estaba incluido)

### 2. Modificación de `vercel.json`:
- Añadir una nueva regla de ruta: `{ "src": "/api/(.*)", "dest": "app/main.py" }`
- Esta regla redirige todas las solicitudes que comienzan con `/api/` hacia la aplicación FastAPI principal

## Configuración Final

**app/routes/widgets.py**:
```python
from fastapi import File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi import APIRouter

from app.api import USUARIO_PRINCIPAL, ComandoPayload, app
from modules.ai import pensar_respuesta, pensar_respuesta_imagen, procesar_intencion_natural
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos, obtener_tareas_pendientes

router = APIRouter()

@router.get("/dashboard")
def api_widget_dashboard(usuario_id: str = ""):
    # ... implementación del endpoint
```

**vercel.json**:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/telegram/(.*)",
      "dest": "app/main.py"
    },
    {
      "src": "/api/(.*)",
      "dest": "app/main.py"
    },
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

## Verificación

Después de aplicar estos cambios, el endpoint `GET https://jarvis.vercel.app/api/widget/dashboard` debería devolver `HTTP 200 OK` con el objeto JSON esperado que incluye las cuentas (`nu`, `nequi`, `efectivo`).

## Enlaces Wiki

- [[Jarvis/estado_proyecto.md]]
- [[Jarvis/Vercel.md]]
- [[Jarvis/monitoreo_uptimerobot.md]]
- [[Jarvis/Índice Principal.md]]