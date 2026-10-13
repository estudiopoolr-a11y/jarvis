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
detallado devuelve una intención admitida; las consultas generales pasan al
generador conversacional `pensar_respuesta`. El bot no convierte esas consultas
en mensajes estáticos de inicialización.

## Interceptores de Seguridad (Anti-Alucinaciones)

Dos interceptores se ejecutan ANTES de cualquier LLM (Gemini/NVIDIA):

1. **Financiero** (`modules/finance/interceptor.py`): Detecta palabras clave como presupuesto, gasto, balance, ingreso, deuda. Resuelve directamente desde Firestore sin pasar por IA.
2. **Tareas** (`app/routes/telegram.py`, función `detectar_e_interactuar_tareas`): Intercepta consultas de tareas ("qué tareas tengo", "anotar tarea", etc.) y las gestiona directamente con Firestore, evitando que los LLM inventen IDs o estados.

## Estructura de Datos en Firebase

### Colecciones Financieras

Los datos del dashboard y los widgets se leen directamente de **Firestore** (proyecto `jarvis-be47a`) desde
`modules/finance/dashboard.py`. El script `scripts/seed_finanzas_2026.py` ingesta el año 2026 en estas colecciones raíz:

- `transactions/{YYYY-MM}/items` — 1 ingreso (`type: "income"`) + N gastos (`type: "expense"`) por mes.
- `categories` — catálogo con `nombre`, `budget`, `tipo`, `icono`, `color`.
- `loans` — documentos con `persona`, `monto`, `monto_original`, `monto_pagado`, `monto_pendiente`, `fecha`, `status`, `pagos`.
- `finanzas/2026` — nodo resumen con `ingresos`, `gastos_por categoría` y `prestamos_detalle`.
- `budgets/{YYYY-MM}/items` — límites presupuestales por categoría para cada mes.

### Colección de Tareas

El subsistema de tareas usa la estructura jerárquica `tasks/{user_id}/items/{task_id}` gestionada por
`modules/tasks/firebase_manager.py`. Cada documento contiene:

- `id` — ID único generado por Firestore.
- `titulo` — descripción de la tarea.
- `descripcion` — detalles adicionales (opcional).
- `completada` — booleano (`false` = pendiente, `true` = completada).
- `fecha_creacion` — marca temporal ISO 8601.
- `usuario_id` — referencia al propietario.

El interceptor de tareas en el webhook de Telegram responde a comandos como "qué tareas tengo",
"anotar tarea X", "todas mis tareas" consultando directamente Firestore sin pasar por ningún LLM.

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
