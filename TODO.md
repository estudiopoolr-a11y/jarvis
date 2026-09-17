# 📋 JARVIS - Lista de Tareas y Hoja de Ruta (TODO List)

> **Documento vivo para desarrolladores y agentes de IA (Claude, Gemini, Antigravity, Cursor, Copilot).**  
> Última actualización: Septiembre 2026

---

## 🧭 Visión General del Proyecto

JARVIS es un asistente ejecutivo y financiero personal integrado con Discord, FastAPI y Google Gemini, respaldado por Firebase Firestore (modelo Kebo).  
Está desplegado 24/7 en **Render.com** mediante dos servicios independientes:
1. **Background Worker** (`jarvis_discord.py`): Bot de Discord 24/7.
2. **Web Service** (`server.py`): API REST y Dashboard HTML.

### Flujo Central de Mensajes
```
Mensaje Discord / Audio
       │
       ▼
bot/events.py (limpieza de menciones)
       │
       ├──> ¿Es intención determinística? ──> procesar_intencion_natural() ──> [Firestore directo] ──> Respuesta inmediata
       │                                                                                                    │
       └──> No (complejo / conversacional) ───────────────────────────────────────────────────────────────┘
                     │
                     ▼
             pensar_respuesta() con contexto financiero inyectado ──> Gemini API (con rotación de keys) ──> Respuesta
```

---

## 📊 Estado Actual del Tablero

### 🟢 1. Completado Recientemente (Septiembre 2026 - v3.1)

- [x] **CRUD Completo de Presupuestos en Firestore (Kebo Style)**:
  - `establecer_presupuesto_mes`: Creación y actualización múltiple por mes (`users/{userId}/budgets/{YYYY-MM}/items`).
  - `modificar_presupuesto_mes`: Edición de montos de presupuestos existentes.
  - `renombrar_presupuesto_mes`: Renombramiento de categoría manteniendo el presupuesto.
  - `eliminar_presupuesto_mes`: Eliminación de presupuesto individual.
  - `eliminar_todos_presupuestos_mes`: Borrado masivo de todos los presupuestos de un mes.
- [x] **Inferencia de Miles en Notas de Voz**:
  - `es_audio=True` transmitido desde `bot/events.py` a `procesar_intencion_natural`.
  - Montos `< 1000` en contexto de presupuesto se normalizan automáticamente multiplicando por 1,000 (ej: `150` -> `$150,000`).
- [x] **Parser Bidireccional de Lenguaje Natural**:
  - Reconocimiento de categorías antes del monto (`mamá 150.000`) y después del monto (`150 para mamá`).
  - Limpieza agresiva de muletillas, saludos (`hola yerbis`), conectores y nombres de meses.
- [x] **Búsqueda Difusa de Categorías**:
  - Función `_coincidir_categoria` en `modules/db.py` insensible a tildes, mayúsculas y puntuación.
- [x] **Consulta de Dinero y Balance Inmediata**:
  - Detección determinística para consultas como `@Jarvis cuanto dinero tengo disponible` o `cuanta plata tengo`.
- [x] **Corrección de Scoping en Python**:
  - Eliminación de imports locales redundantes (`import re`) dentro de bloques condicionales que producían `UnboundLocalError`.

---

### 🟡 2. Tareas Inmediatas / Próximo Sprint (Alta Prioridad)

- [ ] **Limpieza de Documentos Corruptos en Firestore**:
  - *Contexto*: Pruebas anteriores con el parser viejo crearon documentos con nombres como `"Hola, Yerbis. Yerbis, Puedes Poner"` y `"Mamá Deudas,"`.
  - *Acción*: Ejecutar el comando en Discord `borra todos los presupuestos de septiembre` o crear un script en `modules/mantenimiento.py` para purgar documentos con nombres anómalos.
- [ ] **Suite de Pruebas Unitarias Automatizadas (`tests/`)**:
  - *Contexto*: El parser determinístico tiene múltiples regex y stop-words que deben verificarse contra regresiones.
  - *Acción*: Crear `tests/test_parsers.py` con `pytest` cubriendo:
    - `_parse_presupuesto_multiple` (texto y notas de voz con y sin conectores).
    - `_parse_editar_presupuesto` (cambios de monto).
    - `_parse_renombrar_presupuesto` (cambios de nombre de categoría).
    - `_parse_borrar_presupuesto` (individual y masivo `todos`).
    - `_coincidir_categoria` (tildes, mayúsculas, substrings).
- [ ] **Confirmación para Borrado Masivo**:
  - *Contexto*: Si un usuario dice `borra todos los presupuestos de septiembre`, se eliminan sin confirmación previa.
  - *Acción*: Solicitar confirmación interactiva (botón de Discord o comando de confirmación `!confirmar`) antes de ejecutar `eliminar_todos_presupuestos_mes`.
- [ ] **GitHub Actions CI para Tests**:
  - *Acción*: Agregar un workflow `.github/workflows/test.yml` que corra `pytest` en cada push a `main` antes de que Render despliegue.

---

### 🔵 3. Gestión Financiera & Modelo Kebo (Prioridad Media)

- [ ] **Function Calling Nativo con Gemini Tools**:
  - *Contexto*: Actualmente el fallback a Gemini solo genera texto y no puede modificar la base de datos de forma autónoma.
  - *Acción*: Definir herramientas (`tools` en Google GenAI SDK) para que Gemini pueda invocar `registrar_transaccion`, `crear_meta`, `establecer_presupuesto`, etc., de forma estructurada.
- [ ] **Reportes Financieros en PDF / Excel**:
  - *Acción*: Crear endpoint `/api/reportes/mensual` que genere un balance descargable con gráficos y tablas de transacciones.
- [ ] **Categorización Automática de Gastos**:
  - *Acción*: Enriquecer `modules/db.py:obtener_sugerencias_categoria` con mapeo inteligente de establecimientos colombianos comunes (D1, Éxito, Carulla, Oxxo, etc.).
- [ ] **Manejo de Metas de Ahorro Interactivas**:
  - *Acción*: Agregar comandos directos para metas (`!meta crear [nombre] [monto] [fecha]` y `!meta abonar [nombre] [monto]`).
- [ ] **Transferencias entre Cuentas en Lenguaje Natural**:
  - *Acción*: Parser para frases como `"pasé 50.000 de Bancolombia a Nequi"` invocando `registrar_transferencia`.

---

### 🟣 4. Audio & Multimodal (Prioridad Media/Baja)

- [ ] **Audio Multi-Intención**:
  - *Contexto*: Si el usuario envía un audio largo diciendo *"Hola Jarvis, gasté 20k en taxi y recuérdame pagar la luz mañana"*, actualmente se procesa como una sola intención.
  - *Acción*: Permitir splitting de oraciones compuestas en audios transcritos para ejecutar múltiples acciones atómicas.
- [ ] **OCR de Recibos y Facturas Detallado**:
  - *Acción*: Extraer tabla de productos individuales en `pensar_respuesta_imagen` cuando se sube una foto de factura.
- [ ] **Soporte de Mensajes de Voz en Canales de Voz de Discord**:
  - *Acción*: Conectar bot a canal de voz para interactuar en tiempo real (modo asistente presencial).

---

### ⚙️ 5. Infraestructura y DevOps

- [ ] **Monitoreo de Cuota y Latencia de Gemini**:
  - *Acción*: Logging estructurado del tiempo de respuesta y de las keys activas en `_clientes_cache`.
- [ ] **Dashboard Web Interactivo (`templates/dashboard.html`)**:
  - *Acción*: Integrar Chart.js para visualización de balance mensual, gastos por categoría y estado de presupuestos.
- [ ] **Webhook de Notificaciones Discord para Alertas Críticas**:
  - *Acción*: Verificar que el cron `alertas.py` se dispare periódicamente vía GitHub Actions sin agotar límites de Render.

---

## 📌 Guía Rápida para Agentes de IA

Cuando trabajes en este repositorio, recuerda:
1. **Nunca elimines los parsers determinísticos** en `modules/ai.py`: Filtran el 90% de los mensajes sin consumir cuota de Gemini.
2. **Cuidado con las importaciones dentro de funciones**: Python marcará la variable como local para todo el scope si detecta un `import X` dentro de un condicional.
3. **Estructura Firestore**: Siempre usa `budgets/{YYYY-MM}/items` y normaliza el mes a dos dígitos (`09`, no `9`).
4. **Encoding en Windows**: Asegúrate de que las operaciones de consola o tests manejen UTF-8 (`sys.stdout.reconfigure(encoding='utf-8')`).
