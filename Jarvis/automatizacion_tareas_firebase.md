# Automatización de Tareas en Firebase Firestore

Creada el **2026-10-13**. Consolidación del subsistema de tareas usando Firestore como backend operativo, descartando Notion por sus limitaciones de tasa y latencia.

## Arquitectura

### Estructura de Colecciones

```
tasks/{user_id}/items/{task_id}
├── id             : string (Firestore document ID)
├── titulo         : string (título de la tarea)
├── descripcion    : string (detalles opcionales)
├── completada     : boolean (false = pendiente, true = completada)
├── fecha_creacion : ISO 8601 timestamp
└── usuario_id     : string (referencia al propietario)
```

### Módulo: `modules/tasks/firebase_manager.py`

Funciones expuestas:

| Función | Parámetros | Retorna | Descripción |
|---|---|---|---|
| `obtener_cliente_firestore()` | — | `firestore.Client` | Inicializa y retorna cliente Firestore singleton |
| `agregar_tarea(usuario_id, titulo, descripcion)` | `str, str, str` | `dict` | Crea tarea en `tasks/{user_id}/items/` con ID auto-generado |
| `listar_tareas_pendientes(usuario_id)` | `str` | `list[dict]` | Lista tareas con `completada=false` |
| `listar_todas_tareas(usuario_id)` | `str` | `list[dict]` | Lista todas las tareas (completadas + pendientes) |
| `marcar_tarea_completada(usuario_id, tarea_id)` | `str, str` | `bool` | Marca una tarea específica como completada |
| `eliminar_tarea(usuario_id, tarea_id)` | `str, str` | `bool` | Elimina una tarea por su ID de documento |

### Integración en Webhook Telegram

El interceptor `detectar_e_interactuar_tareas()` en [`app/routes/telegram.py`](../app/routes/telegram.py) se ejecuta como **PASO 0.5**, justo después del interceptor financiero y **antes** de cualquier LLM (Gemini/NVIDIA). Esto garantiza que:

1. Las consultas de tareas nunca pasen por modelos generativos (evita alucinaciones de IDs o estados).
2. Los datos leídos/producidos son siempre los reales de Firestore.
3. El router NLP determinístico (que también maneja tareas vía `modules/nlp/router/main.py`) permanece como respaldo para casos no cubiertos por patrones de texto.

#### Patrones interceptados

| Patrón de texto | Acción |
|---|---|
| "qué tareas tengo", "tareas pendientes", "tareas para hoy", "mis tareas" | Listar pendientes desde Firestore |
| "anotar tarea", "nueva tarea", "agregar tarea", "crear tarea", "añadir tarea" | Crear tarea en Firestore |
| "completar tarea", "tarea completada", "ya hice la tarea" | Instrucción para completar |
| "todas mis tareas", "historial de tareas", "ver todas las tareas" | Listar todas (completadas + pendientes) |
| "eliminar tarea", "borrar tarea", "quitar tarea" | Instrucción para eliminar |

### Compatibilidad Legacy

Las funciones existentes en [`modules/finance/legacy.py`](../modules/finance/legacy.py) (`obtener_tareas_pendientes`, `guardar_tarea`, `marcar_tarea_completada`) operan sobre la colección raíz `tareas` y son usadas por el router NLP (`modules/nlp/actions/tareas.py`). Ambas estructuras coexisten:

- **Colección raíz `tareas`**: legado, usada por router NLP existente (con `usuario_id` embebido en cada documento).
- **Colección `tasks/{user_id}/items`**: nueva estructura jerárquica, usada por el interceptor directo en Telegram.

## Limitaciones

- Los comandos "completar tarea N" y "eliminar tarea N" muestran instrucciones pero aún no procesan la acción directamente; se requiere desarrollo futuro para extraer el número/nombre y llamar a `marcar_tarea_completada()` / `eliminar_tarea()`.
- No hay sincronización bidireccional entre la colección legacy `tareas` y la nueva `tasks/{user_id}/items`.

Tags: [[Firebase]] [[Python]] [[FastAPI]] [[Tareas]]
