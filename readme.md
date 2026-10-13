# JARVIS

JARVIS es una API [[FastAPI]] desplegada como funciones Python Serverless en
[[Vercel]]. Integra un bot de [[Telegram]], análisis de lenguaje natural con
[[Gemini API]], persistencia financiera en [[Firebase]]/Firestore y endpoints
para el widget. `vercel.json` conserva la configuración Zero-Config con
`PYTHONUNBUFFERED=1`; el enrutamiento se descubre desde la aplicación y no
requiere bloques manuales `builds` o `functions`.

## Requisitos

- Python 3.12, definido en `.python-version`.
- Dependencias de `requirements.txt`.
- Variables de entorno `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY` (o
  `GEMINI_API_KEYS`) y `FIREBASE_CREDENTIALS`.
- Para desarrollo local, copia `.env.example` a `.env` y completa valores
  propios. Nunca publiques credenciales.

## Desarrollo y pruebas

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -v tests
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

El webhook prioriza el router determinístico y, cuando este no reconoce el
mensaje, usa `analizar_solicitud_consciente` en `modules/ai.py` para clasificar
la intención con Gemini. Las consultas financieras continúan por el parser
detallado existente; las consultas generales reciben una respuesta generativa.
Las solicitudes de tareas no reconocidas se indican explícitamente y no se
presentan como ejecutadas.

## Despliegue

Conecta el repositorio de GitHub al proyecto Vercel y define las variables
sensibles en **Project Settings → Environment Variables**. Los pushes a la
rama configurada generan despliegues automáticamente. También puedes usar la
CLI de Vercel para un despliegue manual. Verifica el webhook de Telegram y
`GET /api/telegram/health` después del despliegue.

La paridad de runtime, el enrutamiento Zero-Config y el logging serverless se
describen en [[Jarvis/arquitectura_paridad_python_y_vercel.md]]. Consulta
[[Jarvis/consolidacion_vercel_serverless.md]] para el flujo de análisis
consciente.

Tags: [[FastAPI]] [[Vercel]] [[Gemini API]] [[Firebase]] [[Python]] [[Telegram]]
