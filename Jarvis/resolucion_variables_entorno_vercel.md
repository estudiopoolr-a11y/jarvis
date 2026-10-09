# Resolución de Variables de Entorno en Vercel y Endpoint de Salud

## Descripción
Nota técnica que documenta la resolución del estado **Needs Attention** en las variables de entorno de Vercel y la creación del endpoint de diagnóstico `/api/telegram/health` para auditoría en tiempo real.

## Problema Identificado
En el panel de Vercel (**Project → Settings → Environment Variables**), las variables `TELEGRAM_BOT_TOKEN` y `GEMINI_API_KEY` mostraban el estado **"Needs Attention"**, lo que indica que Vercel no pudo validar o inyectar correctamente estos valores en el entorno serverless durante los despliegues recientes.

**Causa raíz**: Las variables de entorno en Vercel requieren confirmación manual tras ciertos cambios de configuración o redeploys, y el estado "Needs Attention" bloquea su inyección efectiva en las Serverless Functions.

## Solución Aplicada

### 1. Corrección Manual en Panel de Vercel (Paso Humano)
1. Acceder a **Vercel Dashboard → Project → Settings → Environment Variables**
2. Localizar `TELEGRAM_BOT_TOKEN` y `GEMINI_API_KEY` con estado **Needs Attention**
3. Clic en menú `...` → **Edit**
4. Confirmar o reingresar el valor del token/clave
5. **Save** para eliminar el estado de alerta
6. Repetir para `GEMINI_API_KEY` si aplica

### 2. Endpoint de Diagnóstico Automatizado: `/api/telegram/health`
Se implementó en `app/routes/telegram.py` un endpoint público GET que permite auditar la carga real de variables en el entorno serverless sin exponer valores sensibles:

```python
@router.get("/health")
async def verificar_salud_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_key = os.getenv("GEMINI_API_KEY")

    estado_token = bool(token and len(token) > 10)
    estado_gemini = bool(gemini_key and len(gemini_key) > 10)

    detalles_bot = None
    if estado_token:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                detalles_bot = resp.json() if resp.status_code == 200 else f"Error HTTP {resp.status_code}"
        except Exception as e:
            detalles_bot = f"Excepción de red: {str(e)}"

    return {
        "status": "ok" if estado_token else "token_missing",
        "telegram_bot_token_present": estado_token,
        "gemini_api_key_present": estado_gemini,
        "telegram_api_response": detalles_bot
    }
```

**Características del endpoint:**
- ✅ No expone valores secretos (solo booleanos de presencia)
- ✅ Valida conectividad real con Telegram API vía `getMe`
- ✅ Timeout de 5s para no bloquear la función serverless
- ✅ Retorna `status: "ok"` o `"token_missing"` para monitoreo automatizado
- ✅ Incluye verificación de `GEMINI_API_KEY` como dependencia crítica

### 3. Verificación Post-Corrección
Tras editar las variables en Vercel y redespelgar (git push):

```bash
# Verificación local (requiere .env.local_vercel)
python -c "import asyncio; from app.routes.telegram import verificar_salud_telegram; print(asyncio.run(verificar_salud_telegram()))"

# Verificación en producción
curl https://jarvis-two-pi-13.vercel.app/api/telegram/health
```

**Resultado esperado:**
```json
{
  "status": "ok",
  "telegram_bot_token_present": true,
  "gemini_api_key_present": true,
  "telegram_api_response": {
    "ok": true,
    "result": {"id": 8647134091, "is_bot": true, "first_name": "Jarvis-Asistente", "username": "Pooles_Bot", ...}
  }
}
```

### 4. Verificación Producción Confirmada (2026-10-09)
Tras consolidar las rutas de Telegram en `app/main.py` para evitar errores de importación serverless:

```bash
python scripts/check_prod_health.py
```

Resultado verificado:
```json
{
  "status": "ok",
  "telegram_bot_token_present": true,
  "gemini_api_key_present": true,
  "telegram_api_response": {
    "ok": true,
    "result": {"id": 8647134091, "is_bot": true, "first_name": "Jarvis-Asistente", "username": "Pooles_Bot"}
  }
}
```

Estado actual: **Variables de entorno inyectadas y operativas en Vercel Serverless ✅**

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] - Bitácora de avances y registro de estado.
- [[Índice Principal.md]] - Nodo central de navegación.
- [[Jarvis/telegram_bot_webhook.md]] - Arquitectura del webhook de Telegram.
- [[Vercel]] - Infraestructura serverless.
- [[FastAPI]] - Framework API.
- [[Telegram]] - Plataforma de mensajería.
- [[Python]] - Lenguaje de programación.
