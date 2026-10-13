# Debug: Corrección de Inicialización Firebase en Módulo de Tareas

## Fecha
2026-10-13 15:15 (UTC-05:00)

## Problema Identificado

El módulo de tareas (`modules/tasks/firebase_manager.py`) causaba el error:

```
ValueError: The default Firebase app does not exist. Make sure to initialize 
the SDK by calling initialize_app().
```

Cuando se intentaba usar las funciones `listar_tareas_pendientes()` o `agregar_tarea()` desde el webhook de Telegram.

## Causa Raíz

El módulo importaba directamente `firestore.client()` sin inicializar Firebase primero:

```python
# CODIGO INCORRECTO (ANTES)
import firebase_admin
from firebase_admin import firestore

def obtener_cliente_firestore():
    db = firestore.client()  # <-- Falla porque Firebase no está inicializado
    return db
```

Firebase requiere inicialización explícita con credenciales antes de poder usar `firestore.client()`.

## Solución Aplicada

Cambiar para usar el cliente compartido del proyecto que maneja la inicialización automáticamente:

```python
# CODIGO CORREGIDO (DESPUES)
from modules.firestore.client import get_db

def obtener_cliente_firestore():
    db = get_db()  # <-- Usa el cliente compartido que inicializa Firebase
    return db
```

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `modules/tasks/firebase_manager.py` | Usar `get_db()` en vez de `firestore.client()` |
| `Jarvis/estado_proyecto.md` | Registrar corrección |

## Verificación

### Prueba Local
```powershell
python -c "from modules.tasks.firebase_manager import agregar_tarea, listar_tareas_pendientes"
# ✅ Funciona sin errores
```

### Prueba de Webhook
```powershell
# Crear tarea
POST /api/telegram/webhook {"message":{"chat":{"id":123456789},"text":"anotar tarea comprar pan"}}
# Status: ok (error_handled es normal porque chat_id es inválido)

# Listar tareas  
POST /api/telegram/webhook {"message":{"chat":{"id":123456789},"text":"qué tareas tengo pendientes"}}
# Status: ok
```

### Tests
- 30 tests pasando
- GitHub Actions #147 y #148: ✅ SUCCESS

## Estado Actual del Sistema

| Componente | Estado | Nota |
|------------|--------|------|
| Interceptor Financiero | ✅ OK | Consulta Firestore directamente |
| Módulo de Tareas | ✅ FIXED | Ya usa cliente compartido |
| NVIDIA NIM | ✅ OK | Modelo actualizado a llama-3.3-70b |
| Gemini API | ⚠️ SATURADO | 503 errors frecuentes |
| Health Check | ✅ OK | Token y API keys presentes |

## Comandos Git

```bash
git log --oneline -3
# bc225db docs: registrar corrección de inicialización Firebase en módulo de tareas
# 1d145ab fix(tasks): corregir inicialización de Firebase en módulo de tareas
# 3ce4f4f docs: agregar diagnóstico del sistema al índice principal
```

## Tags
[[Firebase]], [[Python]], [[FastAPI]], [[Tareas]], [[Debug]]
