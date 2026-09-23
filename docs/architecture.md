# 🏗️ Arquitectura de JARVIS

## Visión General

JARVIS es un asistente financiero ejecutivo que funciona 24/7 en modo híbrido:
- **Determinístico (90% de casos)**: Parsers regex ultrarrápidos en Python, sin costo, respuesta en milisegundos.
- **Generativo (10% restante)**: Google Gemini 2.5 Flash con rotación de API keys para conversaciones complejas.

## Stack Tecnológico

| Componente | Tecnología | Ubicación |
|---|---|---|
| **Bot de Discord** | discord.py, Python 3.10+ | `jarvis_discord.py` (Render background worker) |
| **API Web** | FastAPI | `server.py` (Render web service) |
| **Base de Datos** | Firebase Firestore | Kebo-style schema (users/{userId}/...) |
| **Audio/Transcripción** | Google Gemini Audio API | Soporta notas de voz en Discord |
| **LLM Fallback** | Google Gemini 2.5 Flash Lite | Rotación de API keys (`GEMINI_API_KEYS`) |
| **Dashboard** | HTML5 + Vanilla JS | `app/routes.py` -> `/api/dashboard` |
| **Hosting** | Render.com | 2 servicios: Background Worker + Web Service |
| **Keepalive** | UptimeRobot | Ping periódico a `GET /` y `HEAD /` |

## Flujo de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│ Usuario en Discord                                              │
│ @Jarvis gaste 50k en comida                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
           ┌───────────────────────────────────┐
           │ bot/events.py:on_message          │
           │ • Limpia menciones <@ID>          │
           │ • Soporta audio (es_audio=True)   │
           └──────────────┬────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │ procesar_intencion_natural()                │
        │ (modules/ai.py)                             │
        │                                             │
        │ Parsers determinísticos:                    │
        │ • _parse_transaccion                        │
        │ • _parse_presupuesto_multiple               │
        │ • _parse_borrar_presupuesto                 │
        │ • _parse_listar_categorias (v3.2)           │
        │ • _parse_analisis_financiero (v3.2)         │
        │ • _parse_sobrante (v3.2)                    │
        │ • ... (30+ parsers)                         │
        │                                             │
        │ 90% de casos retornan string → SALIDA       │
        └────────┬─────────────────────────────────────┘
                 │
         Retorna None (10%)
                 │
                 ▼
      ┌──────────────────────────┐
      │ pensar_respuesta()       │
      │ (modules/ai.py)          │
      │                          │
      │ • Inyecta contexto       │
      │   etiquetado por periodo │
      │ • Llamada a Gemini       │
      │ • Rotación de API keys   │
      └──────────┬───────────────┘
                 │
                 ▼
      ┌──────────────────────────┐
      │ Google Gemini 2.5 Flash  │
      │ (Fallback generativo)    │
      │                          │
      │ SYSTEM_INSTRUCTION:      │
      │ • Solo lectura           │
      │ • No mezclar periodos    │
      │ • Tono amable, no frío   │
      └──────────┬───────────────┘
                 │
                 ▼
      ┌──────────────────────────┐
      │ Respuesta a Discord      │
      │ o FastAPI client         │
      └──────────────────────────┘
```

## Estructura de Carpetas

Las fachadas `modules/ai.py` y `modules/db.py` se conservan únicamente para
compatibilidad con integraciones antiguas. El código nuevo debe depender del
módulo especializado: los parsers no escriben datos, las acciones del router
son las únicas que mutan Firestore y Gemini permanece en solo lectura. Esto
permite cargar y modificar un dominio (por ejemplo, presupuestos o metas) sin
mezclarlo con los demás.

```
jarvis/
├── bot/                          # Discord bot
│   ├── events.py                # Listener de mensajes
│   ├── handlers/                # Handlers por tipo (finanzas, tareas, metas)
│   ├── services/
│   │   ├── ai.py               # Llamadas a Gemini
│   │   └── db.py               # Operaciones Firebase
│   └── state.py                # Estado de conversaciones
│
├── app/                          # API FastAPI
│   ├── main.py                 # Entrada principal
│   ├── routes/                 # Endpoints REST (dashboard, comando, kebo/, admin, cron, widgets)
│   │   └── kebo/               # Rutas Kebo por dominio (accounts, transactions, budgets, reports, export, seed)
│   ├── services/               # Lógica de negocio
│   └── middleware/
│
├── modules/                      # Módulos compartidos
│   ├── ai.py                   # Fachada de compatibilidad pública
│   ├── nlp/                    # Router, parsers, acciones y confirmaciones
│   │   ├── parsers/            # Reconocimiento de intención, sin escrituras
│   │   ├── actions/            # Ejecución determinística por dominio
│   │   ├── router.py           # Orquesta parser → acción
│   │   └── confirmations.py    # Estado efímero para acciones destructivas
│   ├── gemini/                 # Cliente, transcripción y fallback de solo lectura
│   ├── firestore/              # Inicialización y referencias de Firestore
│   ├── finance/                # Cuentas, presupuestos, categorías y transacciones
│   │   ├── budgets/            # Gestión de presupuestos
│   │   └── transactions/       # Gestión de transacciones (create, transfer, future, recent, search, split)
│   ├── goals/                  # Metas de ahorro
│   ├── reminders/              # Recordatorios y recurrentes
│   ├── db.py                   # Fachada de compatibilidad para código anterior
│   ├── alertas.py              # Sistema de alertas
│   └── importador_txt.py       # Parser de archivos TXT
│
├── tests/                        # Tests unitarios
│   ├── test_parsers.py         # Tests de parsers (20/20 OK ✅)
│   └── test_importador_txt.py
│
├── scripts/                      # Scripts de mantenimiento
│   ├── cleanup_budgets_sep2026.py  # Limpieza de datos corruptos
│   └── migrar_sep_a_ago.py
│
├── docs/                         # Documentation-as-Code (v3.2)
│   ├── architecture.md          # Este archivo
│   ├── database-schema.md       # Esquema Firestore Kebo
│   └── api-endpoints.md         # Contratos FastAPI
│
├── AGENTS.md                     # Guía para agentes IA (actualizado v3.2)
├── CLAUDE.md                     # Configuración de workspace (future)
├── TODO.md                       # Roadmap vivo
└── README.md                     # Descripción del proyecto
```

## Ciclo de Vida de un Mensaje

### 1. Entrada (Discord Bot)

```python
# bot/events.py:on_message
mensaje = "@Jarvis gaste 50k en comida"
usuario_id = "1536228767180136498"
es_audio = False

# Limpieza de menciones
texto_limpio = re.sub(r"<@!?\d+>", "", mensaje)  # → "gaste 50k en comida"

# Intención determinística
respuesta = procesar_intencion_natural(texto_limpio, usuario_id, es_audio)
```

### 2. Parser Determinístico (90% de casos)

```python
# modules/ai.py:procesar_intencion_natural
# Orden de evaluación:

# 0. Asesoría de inversión
if _es_intencion_inversion(texto):
    return _asesorar_inversion(prompt, usuario_id)

# 0b. Consultas financieras (v3.2)
if _parse_listar_categorias(texto):
    return formato_categorias(usuario_id)

if _parse_analisis_financiero(texto):
    return formato_analisis_mes(usuario_id)

if _parse_sobrante(texto):
    return explicacion_sobrante(usuario_id)

# 1. Limpieza de BD
if "borra" in texto and "datos" in texto:
    return limpiar_y_cargar_datos_dinamicos(...)

# 2. Transacciones
transaccion = _parse_transaccion(texto)
if transaccion:
    registrar_transaccion_v2(usuario_id, ...)
    return "💸 Gasto registrado: -$50,000 en Comida"

# ... 30+ parsers más

# Si nada matchea → None → caer a Gemini
return None
```

### 3. Generativo (10% de casos: cae a Gemini)

```python
# modules/ai.py:pensar_respuesta
contexto = obtener_contexto_financiero(usuario_id)

# Contexto etiquetado (v3.2)
# LIQUIDEZ_CUENTAS=$561,992 |
# MES_ACTUAL(2026-09): Ing=$X Gas=$Y Neto=$Z |
# PRESUPUESTOS_MES={...} |
# HISTORICO: Ing=$A Gas=$B Neto=$C |
# MOV_ACTUAL=[...]

prompt = f"{SYSTEM_INSTRUCTION}\n{contexto}\nMensaje: {prompt_usuario}"

respuesta = gemini.generate_content(
    contents=prompt,
    tools=[google_search],  # Si necesita contexto web
)
return respuesta.text
```

## Garantías de Coherencia

| Aspecto | Garantía |
|---|---|
| **Idioma** | Español (Colombia) con tolerancia a typos, mayúsculas y acentos |
| **Moneda** | COP (pesos colombianos). Inferir miles en audio si monto < 1000 |
| **Periodos** | NUNCA mezclar presupuestos de un mes con gastos históricos |
| **Categorías** | `_coincidir_categoria()` normaliza acentos, mayúsculas, puntuación |
| **Tono** | Amable, directo. NUNCA regañar ni contradecir al usuario |
| **Mutaciones** | Solo parsers determinísticos escriben a Firestore. Gemini es solo lectura |
| **Borrado masivo** | Requiere `confirmar presupuestos` dentro de cinco minutos; `cancelar presupuestos` lo anula |
| **Velocidad** | Parsers en <10ms. Gemini <3s. No importa si es determinístico o generativo |

## Despliegue

### Servicios en Render.com

**Background Worker** (`jarvis_discord.py`):
- Corre indefinidamente
- Escucha eventos de Discord
- No expone puertos

**Web Service** (`server.py`):
- FastAPI en puerto 5000
- Mantenido despierto por UptimeRobot
- Endpoints: `/api/dashboard`, `/api/finanzas/...`, etc.

### Variables de Entorno Requeridas

```bash
DISCORD_TOKEN=...
GEMINI_API_KEYS=key1,key2,key3,...  # Rotación
FIREBASE_CREDENTIALS=...            # JSON
RENDER_DEPLOY_HOOK=...              # Webhooks
```

## Versiones

| Versión | Cambios |
|---|---|
| v3.0 | CRUD de presupuestos, parsers básicos |
| v3.1 | Limpieza de datos corruptos, README actualizado |
| v3.2 | Parsers de consulta (categorías, análisis, sobrante), contexto etiquetado por período, tono mejorado |

---

**Última actualización**: 2026-09-17 (v3.2)
**Mantenedor**: Pool (desarrollador) + Claude Code (agente IA)
