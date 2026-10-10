# Arquitectura de Paridad Python y Vercel

## Causa raíz de la fricción en Serverless

- **Cold starts**: Inicialización tardía de funciones serverless en Vercel afecta tiempos de respuesta.
- **Diferencias de runtime**: Versión de Python en desarrollo local vs. Vercel puede divergir, provocando `ModuleNotFoundError`.
- **Buffering de logs**: Python en Vercel Serverless bufferiza stdout/stderr, retrasando visibilidad de logs en Vercel Live Logs.

## Solución aplicada

1. **Fijación de versión Python**:
   - Archivo `.python-version` con `3.12` para asegurar consistencia entre entornos.

2. **Desbufferización de logs**:
   - Variable `PYTHONUNBUFFERED=1` inyectada en `vercel.json` bajo `env`.
   - Fuerza emisión inmediata de logs.

3. **Auditoría de entorno**:
   - Script `scripts/audit_environment_parity.py` verifica versión activa de Python, presencia de dependencias críticas (`fastapi`, `uvicorn`, `httpx`, `PIL`, `yfinance`, `google.generativeai`) y carga exitosa de `app.main`.

## Enlaces Wiki obligatorios

- [[Jarvis/estado_proyecto.md]]
- [[Índice Principal.md]]
- [[FastAPI]]
- [[Vercel]]

## Referencias

- [[Jarvis/resolucion_logging_unbuffered_y_despacho_telegram.md]] — Solución de logging con `flush=True`.
- [[Jarvis/telegram_bot_webhook.md]] — Arquitectura técnica del enrutador.
