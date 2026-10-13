# JARVIS

JARVIS es una API [[FastAPI]] desplegada como funciones Python Serverless en
[[Vercel]]. Integra un bot de [[Telegram]], análisis de lenguaje natural con
[[Gemini API]], persistencia en [[Firebase]]/Firestore y endpoints para el
widget. El backend usa `modules/firestore/client.py` como cliente compartido
de persistencia. `vercel.json` conserva la configuración Zero-Config con
`PYTHONUNBUFFERED=1`; el enrutamiento se descubre desde la aplicación y no
requiere bloques manuales `builds` o `functions`.

## Requisitos

- Python 3.12, definido en `.python-version`.
- Dependencias de `requirements.txt`.
- Variables de entorno `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY` (o
  `GEMINI_API_KEYS`) y `FIREBASE_CREDENTIALS`.
- Opcional: `NVIDIA_API_KEYS` (múltiples claves separadas por comas) para rotación automática y fallback cuando Gemini está saturado.
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
la intención con Gemini. Ejecuta una acción financiera solo si el parser
detallado devuelve una intención admitida; las consultas generales, las tareas
no reconocidas y las clasificaciones financieras no concluyentes pasan al
generador conversacional `pensar_respuesta`. El bot no convierte esas consultas
en mensajes estáticos de inicialización.

El dashboard web (`/api/finanzas/resumen`) y el widget iOS
(`/api/widget/resumen`, `/api/widget/dashboard`) comparten los agregados
mensuales de Firestore en `modules/finance/dashboard.py`: transacciones,
presupuestos y cuentas. Los importes usan los campos Kebo y sus alias legacy.
Si Firebase no está disponible o falla una lectura, las APIs responden con
error HTTP en vez de presentar cifras cero como datos exitosos.

## Estructura de Datos Financieros en Firebase

Los datos del dashboard y los widgets se leen directamente de **Firestore** (proyecto `jarvis-be47a`) desde
`modules/finance/dashboard.py`. El script `scripts/seed_finanzas_2026.py` ingesta el año 2026 en estas colecciones raíz:

- `transactions/{YYYY-MM}/items` — 1 ingreso (`type: "income"`) + N gastos (`type: "expense"`) por mes.
- `categories` — catálogo con `nombre`, `budget`, `tipo`, `icono`, `color`.
- `loans` — documentos con `persona`, `monto`, `monto_original`, `monto_pagado`, `monto_pendiente`, `fecha`, `status`, `pagos`.
- `finanzas/2026` — nodo resumen con `ingresos`, `gastos_por categoría` y `prestamos_detalle`.

El script es idempotente: salta meses que ya tienen transacciones, no duplica categorías y omite loans que
coincidan en `(persona, fecha, monto)`. Para re-ejecutarlo, borra los nodos manualmente o modifica los datos fuente.

**Limitaciones:** no se definieron límites de presupuesto, así que `porcentaje_uso` es `0.0` hasta que se
creen documentos en `budgets/{YYYY-MM}/items`. El dashboard muestra el mes actual por defecto; los meses
anteriores se consultan con `?mes=2026-07` en la API o `mes="2026-07"` en el código.

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

Consulta [[Jarvis/arquitectura_dashboard_y_widgets.md]] para el flujo de datos
financieros del dashboard y los widgets.

Tags: [[FastAPI]] [[Vercel]] [[Gemini API]] [[Firebase]] [[Python]] [[Telegram]] [[Dashboard]]
