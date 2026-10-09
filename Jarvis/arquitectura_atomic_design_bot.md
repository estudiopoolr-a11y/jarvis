# Arquitectura Atomic Design — Bot JARVIS

> **Estado:** Implementado  
> **Fecha:** 2026-10-08  
> **Archivo fuente:** `app/core/`  
> **Consumidor principal:** `app/routes/telegram.py`

---

## ¿Qué es Atomic Design?

**Atomic Design** es un patrón de diseño desarrollado por Brad Frost que propone construir interfaces (y en este caso, lógica de software) a partir de componentes cada vez más complejos, organizados en 5 capas jerárquicas:

1. **Átomos** → Primitivas indivisibles
2. **Moléculas** → Combinaciones de átomos
3. **Organismos** → Conjuntos de moléculas con lógica de negocio
4. **Plantillas** → Estructuras base para layouts/respuestas
5. **Páginas/Rutas** → Puntos de entrada que ensamblan todo

---

## Capas Implementadas en JARVIS

### 1. Átomos (`app/core/atoms/`)
Funciones puras, sin efectos secundarios, que operan sobre datos simples.

| Función | Archivo | Responsabilidad |
|---|---|---|
| `atomo_formatear_moneda(monto)` | `formatters.py` | Convierte `float` → string COP (ej: `$1.500.000 COP`) |
| `atomo_obtener_emoji_estado(porcentaje)` | `formatters.py` | Retorna `🔴`, `🟡` o `🟢` según umbral de porcentaje |

**Principio:** Cada átomo es testeable de forma aislada y no depende de otros módulos del proyecto.

### 2. Moléculas (`app/core/molecules/`)
Combinan uno o más átomos para formar componentes visuales reutilizables.

| Función | Archivo | Responsabilidad |
|---|---|---|
| `molecula_tarjeta_balance(saldo, gastos, limite)` | `cards.py` | Ensambla tarjeta de resumen financiero con emoji + moneda |
| `molecula_tarjeta_presupuesto(categoria, asignado, gastado, limite)` | `cards.py` | Ensambla tarjeta detallada por categoría presupuestal |

**Principio:** Las moléculas encapsulan formato visual sin lógica de negocio (sin BD, sin HTTP).

### 3. Organismos (`app/core/organisms/`)
Módulos con lógica de negocio que orquestan moléculas, consultan fuentes de datos y devuelven respuestas completas.

| Clase | Archivo | Responsabilidad |
|---|---|---|
| `OrganismoFinanzas` | `finance_organism.py` | Coordina consultas financieras y retorna tarjetas formateadas |

**Métodos:**
- `obtener_resumen_organismo(user_id)` → retorna tarjeta balance consolidado
- `obtener_detalle_presupuestos(user_id)` → retorna listado de tarjetas por categoría

**Principio:** Los organismos pueden tener inyección de dependencias (`db_connector`) para separar lógica de datos de lógica de presentación.

### 4. Plantillas (`app/core/templates/`)
Formatos estructurales reutilizables para respuestas de Telegram.

| Constante/Función | Archivo | Responsabilidad |
|---|---|---|
| `PLANTILLA_RESPUESTA_BASE` | `telegram_templates.py` | Diccionario con mensajes fijos (/start, /ayuda, errores) |
| `plantilla_comando_balance()` | `telegram_templates.py` | Retorna bienvenida/comandos disponibles |
| `plantilla_respuesta_nlp(fallback)` | `telegram_templates.py` | Retorna mensaje de mantenimiento o vacío |

### 5. Páginas / Rutas (`app/routes/telegram.py`)
Punto de entrada ASGI que consume organismos y plantillas para servir la integración con Telegram.

**Flujo de datos:**
```
Telegram POST /api/telegram/webhook
  └─> Route handler (telegram.py)
       ├─> /balance → OrganismoFinanzas().obtener_resumen_organismo()
       │              └─> molecula_tarjeta_balance()
       │                   └─> atomo_obtener_emoji_estado() + atomo_formatear_moneda()
       ├─> /start|/ayuda → plantilla_comando_balance()
       └─> NLP natural → modules.ai + modules.intent_handler
```

---

## Diagrama de Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Petición Telegram                            │
│                     POST /api/telegram/webhook                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RUTA (Page)  app/routes/telegram.py                                │
│  - Parsea payload JSON                                               │
│  - Extrae text, chat_id, user_id                                     │
│  - Enruta a comando específico                                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐ ┌──────────────────┐ ┌────────────────────┐
│ ORGANISMO       │ │ ORGANISMO        │ │ PLANTILLA          │
│ Finanzas        │ │ (futuro: NLP     │ │ Telegram           │
│                 │ │    response)     │ │                    │
│ obtener_resumen │ │                  │ │ /start, /ayuda,    │
│                 │ │                  │ │ error messages     │
└────────┬────────┘ └──────────────────┘ └────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  MOLÉCULA  molecula_tarjeta_balance(saldo, gastos, limite)           │
│  - Calcula porcentaje                                                │
│  - Invoca átomos                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
┌─────────────────────────┐    ┌──────────────────────────┐
│ ÁTOMO                   │    │ ÁTOMO                    │
│ atomo_obtener_emoji_    │    │ atomo_formatear_moneda() │
│ estado(pct)             │    │                          │
│ → "🔴" | "🟡" | "🟢"   │    │ → "$1.500.000 COP"       │
└─────────────────────────┘    └──────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RESPUESTA ENSAMBLADA (Markdown)                                     │
│  "🟡 *Balance*: $1.500.000 COP"                                      │
│   📉 *Gastos del Mes*: $450.000 COP (45.0%)"                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                    Telegram sendMessage API
```

---

## Beneficios de esta Arquitectura

1. **Reutilización:** Los átomos y moléculas pueden consumirse desde cualquier ruta (Telegram, widgets, API REST, cron jobs).
2. **Testeabilidad:** Cada capa es aislable; se pueden escribir tests unitarios para átomos y moléculas sin dependencias externas.
3. **Mantenibilidad:** Un cambio en el formato de moneda solo requiere modificar `atomo_formatear_moneda()`.
4. **Extensibilidad:** Nuevos organismos pueden agregarse sin tocar las capas inferiores.
5. **Separación de responsabilidades:** La ruta (telegram.py) solo orquesta; no contiene lógica de negocio ni formato.

---

## Integración con otros Módulos

- [[Hermes Agent]] — El motor de inteligencia sigue operando en `modules/ai.py`; los organismos atómicos consumen sus resultados cuando se requiere procesamiento NLP avanzado.
- [[Módulo de Finanzas]] — Los organismos reemplazan gradualmente las llamadas directas a `modules/finance/` en el flujo de Telegram.
- [[Base de Datos Firestore]] — Los organismos están preparados para inyectar conectores de BD (`db_connector`) para consultar datos reales en producción.

---

## Archivos Clave

| Ruta | Capa |
|---|---|
| `app/core/__init__.py` | Inicialización del paquete core |
| `app/core/atoms/formatters.py` | Átomos |
| `app/core/molecules/cards.py` | Moléculas |
| `app/core/organisms/finance_organism.py` | Organismos |
| `app/core/templates/telegram_templates.py` | Plantillas |
| `app/routes/telegram.py` | Página/Ruta (consumidora) |

---

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] - Registro de avances y roadmap.
- [[Jarvis/Índice Principal.md]] - Navegación global del proyecto.
- [[Jarvis/telegram_bot_webhook.md]] - Documentación del webhook de Telegram.
- [[FastAPI]] - API principal.
- [[Vercel]] - Infraestructura serverless.
