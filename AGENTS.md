# 🤖 Guía Operativa para Asistentes de IA (AGENTS.md)

> **Versión**: v3.2 (2026-09-17)
> **Documentación viva**: ver carpeta `docs/` para arquitectura, esquema de BD y API.

Este documento define la arquitectura, convenciones y reglas operativas para cualquier agente de IA (Claude, Gemini, Cursor, Copilot) que colabore en el proyecto **JARVIS**.

---

## 🏛️ Arquitectura del Sistema

JARVIS funciona 24/7 en modo híbrido:

| Modo | Cuándo | Costo | Latencia |
|---|---|---|---|
| **Determinístico** | 90% de mensajes | $0 | <10ms |
| **Generativo** | Cuando ningún parser coincide | Tokens Gemini | <3s |

### Servicios en producción (Render.com)

| Servicio | Archivo | Función |
|---|---|---|
| **Background Worker** | `jarvis_discord.py` | Bot Discord persistente |
| **Web Service** | `server.py` → `app/main.py` | FastAPI + Dashboard |

### Flujo de mensajes

```text
Discord → bot/events.py:on_message
       → procesar_intencion_natural() [modules/ai.py]
       → parsers determinísticos
       → respuesta directa
       → si no hay match: pensar_respuesta() → Gemini
```

Para más detalle, consultar [`docs/architecture.md`](docs/architecture.md).

---

## 🗄️ Base de Datos

Motor: Firebase Firestore, modelo Kebo, con raíz `users/{userId}/`.

```text
users/{userId}/
├── accounts/{accountId}
├── categories/{categoryId}/subcategories/{subcategoryId}
├── budgets/{YYYY-MM}/items/{budgetItemId}
├── transactions/{YYYY-MM}/items/{transactionId}
├── goals/{goalId}
├── recurring/{recurringId}
└── reminders/{reminderId}
```

Reglas críticas:

1. Los periodos usan dos dígitos: `2026-09`, nunca `2026-9`.
2. Un presupuesto es un **techo mensual**, no dinero separado; nunca se resta de `accounts.balance`.
3. Un presupuesto solo se compara con gastos del mismo periodo `YYYY-MM`.
4. El contexto para Gemini debe distinguir `LIQUIDEZ_CUENTAS`, `MES_ACTUAL`, `PRESUPUESTOS_MES` e `HISTORICO`.
5. No guardar tokens, contraseñas ni credenciales bancarias en Firestore o Git.

El esquema completo está en [`docs/database-schema.md`](docs/database-schema.md).

---

## ⚠️ Reglas para agentes

### 1. Preservar parsers determinísticos

- **Nunca** reemplazar parsers de `modules/ai.py` por llamadas directas al LLM.
- Todo parser nuevo debe tener pruebas en `tests/test_parsers.py`.
- Las mutaciones de Firestore deben ejecutarse solamente mediante flujo determinístico explícito.
- Gemini opera en modo de solo lectura y nunca debe afirmar que modificó datos.

### 2. Imports a nivel de módulo

Evitar imports dentro de bloques condicionales porque pueden causar `UnboundLocalError`:

```python
# Correcto
import re

def buscar(texto):
    return re.search(r"...", texto)
```

### 3. Notas de voz

Con `es_audio=True`, un monto menor que 1000 puede representar miles de COP: `150` → `$150,000`.

### 4. Categorías

Usar `_coincidir_categoria()` o `_cat_exacta()` de `modules/db.py`. La comparación tolera acentos, mayúsculas y puntuación, priorizando coincidencia exacta antes de parcial.

### 5. Consultas financieras

- `q categorias hay` debe listar categorías, cuentas y presupuestos, no caer a Gemini.
- `dame un analisis financiero` debe usar el periodo actual por defecto.
- `deja lo que sobra` no crea ni modifica presupuestos automáticamente.
- `ajustar mi balance a los presupuestos` debe explicar que son conceptos diferentes y no mutar saldos.
- No comparar techos de septiembre con gastos históricos.

### 6. Tono

Respuestas directas pero amables:

- No regañar ni contradecir de forma condescendiente.
- Si falta información, explicar qué dato falta.
- En frases ambiguas, ofrecer una interpretación y un comando concreto.

### 7. Windows y UTF-8

```bash
PYTHONIOENCODING=utf-8 py -3 script.py
```

En Python:

```python
sys.stdout.reconfigure(encoding="utf-8")
```

### 8. Cambios en documentación

Cuando cambien arquitectura, esquema o rutas:

1. Actualizar el Markdown correspondiente en `docs/`.
2. Actualizar `AGENTS.md` si cambia una regla operativa.
3. Actualizar tests y ejecutar la suite.
4. Mantener `TODO.md` alineado con el estado real.

---

## 🧪 Verificación

```bash
py -3 -m unittest tests.test_parsers -v
```

Las rutas FastAPI se documentan en [`docs/api-endpoints.md`](docs/api-endpoints.md).

---

## 📚 Archivos de contexto

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/database-schema.md`](docs/database-schema.md)
- [`docs/api-endpoints.md`](docs/api-endpoints.md)
- [`TODO.md`](TODO.md)
- [`README.md`](README.md)
