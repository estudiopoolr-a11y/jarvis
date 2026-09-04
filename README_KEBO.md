# 🏗️ Estructura Kebo en JARVIS

JARVIS migró de una estructura plana de Firestore a una estructura jerárquica estilo **Kebo** (la app de presupuestos que el dueño usa).

## 📁 Nueva estructura

```
users/
  └── {userId}/                           ← "iphone_user"
       │
       ├── accounts/{accountId}           ← Cuentas (Efectivo, Nequi, etc.)
       │
       ├── categories/{catId}             ← Categorías con presupuesto
       │
       ├── transactions/
       │   └── {year}/
       │       └── {month}/               ← "2026/09"
       │           └── items/{txId}       ← Transacciones del mes
       │
       ├── goals/{goalId}                 ← Metas de ahorro
       │
       └── recurring/{recId}              ← Pagos fijos/recurrentes
```

### 📊 Ventajas vs estructura vieja

| Antigua | Nueva |
|---------|-------|
| Colección plana `finanzas/` con TODAS las transacciones mezcladas | Subcol por mes → queries 10× más rápidas |
| Sin cuentas | Saber de dónde sale cada peso |
| `presupuestos/` separado de `categorias/` | Un solo lugar para presupuesto + categoría |
| `metas/` plano | Metas con `current_amount` + `fecha_limite` |
| Sin recurrentes | Próximamente: gastos automáticos recurrentes |

## 🚀 Endpoints nuevos

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/kebo/cuentas?usuario_id=iphone_user` | Lista cuentas con balances |
| GET | `/api/kebo/presupuestos?usuario_id=iphone_user` | Presupuestos + gastado del mes |
| GET | `/api/backup/export?usuario_id=iphone_user` | Exporta TODOS los datos a JSON |
| GET | `/api/backup/migrate?usuario_id=iphone_user` | Migra de estructura vieja a nueva |

## 💬 Comandos de voz nuevos

| Dices | JARVIS hace |
|-------|-------------|
| "mis cuentas" | Lista todas las cuentas con su balance |
| "crea cuenta Nequi tipo débito" | Crea cuenta (detecta tipo automáticamente) |
| "crea cuenta Efectivo con 50000" | Crea cuenta con saldo inicial |
| "saldo nequi" | Muestra el balance de una cuenta específica |
| "cuánto tengo en efectivo" | Idem con variación de frase |

### 🏷️ Tipos de cuenta detectados

| Mencionas | Tipo |
|-----------|------|
| efectivo, cash | 💵 cash |
| débito, nequi, daviplata, bancolombia | 💜 debit |
| crédito | 💳 credit |
| ahorro, ahorros | 🏦 savings |

## 🔧 Compatibilidad con estructura vieja

✅ **Los datos antiguos NO se borran.** Siguen en:
- `finanzas/{id}` → usado por `/api/finanzas/resumen` (widget actual)
- `presupuestos/{id}` → leído por comandos de voz existentes
- `metas/{id}`, `tareas/{id}` → sin cambios

✅ **Escritura nueva usa estructura Kebo:**
- Comandos de voz para gastos → escriben en `users/{userId}/transactions/...`
- Comandos de voz para cuentas → escriben en `users/{userId}/accounts`
- Comandos de voz para presupuestos → escriben en `users/{userId}/categories`

## 📱 Widget Scriptable

Usa [`jarvis_widget.js`](./jarvis_widget.js) para el widget iPhone:

1. Abre la app **Scriptable**
2. Crea un nuevo script
3. Pega el contenido de `jarvis_widget.js`
4. Añade el widget a tu pantalla de inicio
5. Selecciona el script

### Tamaños soportados

- **Pequeño (Small)**: Solo cuentas principales + total
- **Mediano/Grande (Medium/Large)**: Cuentas + resumen mes + top categorías

## 🔄 Migración (cuando decidas)

⚠️ **Por hacer manualmente** (con confirmación tuya):

```bash
# En navegador (con Render deployado):
https://jarvis-h20g.onrender.com/api/backup/migrate?usuario_id=iphone_user
```

Esto:
1. Crea 3 cuentas por defecto: Efectivo, Nequi, Crédito
2. Migra cada presupuesto → categoría con `budget`
3. Migra cada transacción → `transactions/{year}/{month}/items/`
4. Actualiza balances de las cuentas
5. **NO** borra datos antiguos (todo se conserva)

## 📁 Archivos de esta migración

| Archivo | Propósito |
|---------|-----------|
| `modules/database_v2.py` | Capa nueva de BD con funciones Kebo |
| `backup_datos.py` | Script de backup local (no usado - usar endpoint) |
| `migrar_a_kebo.py` | Script de migración local (no usado - usar endpoint) |
| `jarvis_widget.js` | Widget Scriptable para iPhone |
| `README_KEBO.md` | Este archivo |

## 🎯 Estado actual

✅ Migración completada en código
⏸️ **Migración de datos: pausada esperando confirmación del dueño**
✅ Comandos de voz funcionando con nueva estructura
✅ Widget actualizado listo