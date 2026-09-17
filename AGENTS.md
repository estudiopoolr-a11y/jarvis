# 🤖 Guía Operativa para Asistentes de IA (AGENTS.md)

Este documento define la arquitectura, convenciones y reglas operativas para cualquier agente de IA (Claude, Gemini, Antigravity, Cursor, Copilot) que colabore en el proyecto **JARVIS**.

---

## 🏛️ Arquitectura del Sistema

El proyecto está diseñado para funcionar 24/7 de forma híbrida: determinística (parsers regex ultrarrápidos y sin costo) y generativa (Google Gemini con rotación de API keys).

### Servicios en Producción (Render.com)
1. **Background Worker (`jarvis_discord.py`)**:
   - Corre el bot de Discord de forma persistente.
   - Escucha menciones, roles y notas de voz (`bot/events.py`).
2. **Web Service (`server.py`)**:
   - Servidor FastAPI con dashboard visual y endpoints REST (`app/routes.py`).
   - Mantenido despierto mediante ping periódico de UptimeRobot (soporta `GET` y `HEAD /`).

### Flujo de Ejecución de un Mensaje
1. Mensaje llega a `bot/events.py:on_message`.
2. Se limpia mención de bot (`<@ID>`) o rol (`<@&ID>`).
3. Se invoca **`procesar_intencion_natural(texto, usuario_id, es_audio=...)`**:
   - Si retorna un string, **se envía de inmediato** y termina el flujo (90% de los casos).
   - No consume tokens ni cuota de Gemini.
4. Si retorna `None`, cae al flujo generativo:
   - Se inyecta contexto financiero reciente (`obtener_contexto_financiero`).
   - Se invoca `pensar_respuesta()` -> Gemini 2.5 Flash / Flash Lite con rotación de keys (`GEMINI_API_KEYS`).

---

## 🗄️ Esquema de Base de Datos (Firebase Firestore - Kebo Style)

Todas las colecciones principales residen bajo la ruta del usuario:
`users/{userId}/`
- `budgets/{YYYY-MM}/items/{docId}`: Presupuestos mensuales (campos: `category_name`, `category_id`, `amount`, `year`, `month`, `created_at`).
  - **REGLA CRÍTICA**: Siempre normalizar mes con dos dígitos (`09`, no `9`).
- `transactions/{YYYY-MM}/items/{txId}`: Transacciones mensuales (campos: `type`, `amount`, `category_id`, `payee`, `description`, `date`).
- `accounts/{accountId}`: Cuentas bancarias o de efectivo (campos: `name`, `balance`, `type`, `icon`, `color`).
- `categories/{categoryId}`: Categorías personalizadas y predefinidas.
- `goals/{goalId}`: Metas de ahorro.
- `recurring/{recId}`: Pagos recurrentes fijos.

---

## ⚠️ Reglas Operativas y Buenas Prácticas para Agentes

1. **Preservar Parsers Determinísticos**:
   - **NUNCA** elimines ni reemplaces los parsers de `modules/ai.py` por llamadas directas al LLM. Los parsers evitan el error 429 (Rate Limit) y hacen que el bot responda en milisegundos.
2. **Evitar Importaciones Dentro de Scopes Locales**:
   - En Python, si pones `import re` o `from datetime import datetime` dentro de un bloque condicional en una función, Python marcará ese identificador como variable local para toda la función, provocando `UnboundLocalError` en líneas anteriores.
   - Importa siempre a nivel de módulo o con nombres con prefijo si es estrictamente necesario.
3. **Manejo de Notas de Voz (`es_audio=True`)**:
   - En notas de voz, los usuarios suelen decir números como *"150"* o *"205"* para referirse a miles ($150,000 o $205,000 COP). Cuando `es_audio=True` y el monto sea `< 1000`, inferir miles.
4. **Normalización de Nombres de Categoría**:
   - Usa siempre `_coincidir_categoria` en `modules/db.py` para comparar nombres, garantizando tolerancia a acentos, mayúsculas y puntuación.
5. **Windows UTF-8 Safety**:
   - En scripts o comandos de terminal en Windows, asegura `PYTHONIOENCODING="utf-8"` o `sys.stdout.reconfigure(encoding='utf-8')` para evitar excepciones `UnicodeEncodeError` por emojis.
6. **Consulta de Tareas Pendientes**:
   - Consulta y mantén actualizado [`TODO.md`](TODO.md) antes de comenzar o al concluir nuevas funcionalidades.
