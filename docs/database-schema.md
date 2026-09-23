# 🗄️ Esquema de Base de Datos JARVIS

## Motor y Convenciones

- **Motor**: Firebase Firestore
- **Modelo**: Kebo-style, organizado por usuario
- **Ruta raíz**: `users/{userId}/`
- **Moneda base**: COP (pesos colombianos)
- **Fechas**: ISO 8601 (`YYYY-MM-DD`)
- **Meses**: siempre dos dígitos (`2026-09`, nunca `2026-9`)
- **IDs**: IDs automáticos de Firestore salvo documentos de periodo (`YYYY-MM`)

## Diagrama de Colecciones

```
users/{userId}/
├── accounts/{accountId}
├── categories/{categoryId}
│   └── subcategories/{subcategoryId}
├── budgets/{YYYY-MM}/
│   └── items/{budgetItemId}
├── transactions/{YYYY-MM}/
│   └── items/{transactionId}
├── goals/{goalId}
├── recurring/{recurringId}
├── reminders/{reminderId}
├── exchange_rates/{currency}
└── profiles/{profileId}
```

## 1. Accounts (Cuentas)

Ruta: `users/{userId}/accounts/{accountId}`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `nombre` | string | Sí | Nombre visible: `Efectivo`, `Nequi`, `Bancolombia` |
| `type` | string | Sí | `cash`, `savings`, `checking`, `credit`, `investment` |
| `currency` | string | Sí | ISO 4217; por defecto `COP` |
| `balance` | number | Sí | Saldo actual de la cuenta |
| `institution` | string | No | Banco o entidad financiera |
| `bank_last4` | string | No | Últimos cuatro dígitos, no credenciales |
| `icon` | string | No | Emoji/icono visual |
| `color` | string | No | Color hexadecimal del dashboard |
| `created_at` | timestamp | Sí | Creación del registro |

**Regla**: `balance` de una cuenta representa liquidez; no debe calcularse restando presupuestos.

## 2. Categories (Categorías)

Ruta: `users/{userId}/categories/{categoryId}`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `nombre` | string | Sí | Nombre visible de categoría |
| `budget` | number | No | Presupuesto legacy/default; preferir `budgets/{YYYY-MM}` |
| `tipo` | string | No | `fijo` o `variable` |
| `icono` | string | No | Emoji/icono |
| `color` | string | No | Color hexadecimal |
| `created_at` | timestamp | Sí | Creación |

### Subcategorías

Ruta: `users/{userId}/categories/{categoryId}/subcategories/{subcategoryId}`

Campos adicionales habituales: `nombre`, `icono`, `color`, `created_at`.

## 3. Budgets (Presupuestos Mensuales)

Ruta: `users/{userId}/budgets/{YYYY-MM}/items/{budgetItemId}`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `category_id` | string | Sí | ID de `categories` |
| `category_name` | string | Sí | Snapshot legible del nombre |
| `amount` | number | Sí | Techo mensual de gasto |
| `year` | string | Sí | Ej. `2026` |
| `month` | string | Sí | Ej. `09` |
| `created_at` | timestamp | Sí | Creación/actualización |

**Semántica crítica**:
- Un presupuesto es un **techo de gasto**, no dinero separado ni un débito de una cuenta.
- `amount` no se debe restar de `accounts.balance`.
- Las comparaciones presupuesto/gasto deben usar el mismo periodo `YYYY-MM`.
- El helper `establecer_presupuesto_mes` actualiza el item de categoría existente.
- Búsqueda usa `_coincidir_categoria`: exacta normalizada primero, parcial después.

## 4. Transactions (Transacciones)

Ruta: `users/{userId}/transactions/{YYYY-MM}/items/{transactionId}`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `type` | string | Sí | `income`, `expense`, `transfer` |
| `amount` | number | Sí | Monto positivo; el tipo determina signo |
| `category_id` | string | No | ID de categoría |
| `category_name` | string | No | Snapshot legible |
| `account_id` | string | Sí | Cuenta afectada |
| `payee` | string | No | Beneficiario/comercio |
| `description` | string | No | Descripción |
| `fee` | number | No | Comisión |
| `status` | string | No | `pending` o `cleared` |
| `tags` | array[string] | No | Hashtags |
| `date` | string | Sí | `YYYY-MM-DD` |
| `created_at` | timestamp | Sí | Creación |

**Balance**:
- Ingreso: `+amount`
- Gasto: `-amount`
- Transferencia: mueve saldos entre cuentas; no cuenta como ingreso/gasto neto.

## 5. Goals (Metas)

Ruta: `users/{userId}/goals/{goalId}`

Campos: `name`/`nombre`, `target_amount`/`monto_objetivo`, `current_amount`/`monto_actual`, `deadline`/`fecha_limite`, `created_at`.

## 6. Recurring (Pagos Recurrentes)

Ruta: `users/{userId}/recurring/{recurringId}`

Campos: `name`/`nombre`, `amount`/`monto`, `frequency`/`frecuencia`, `day`/`dia`, `category_id`, `account_id`, `created_at`.

## 7. Exchange Rates

Ruta: `users/{userId}/exchange_rates/{currency}`

Campos: `rate`, `updated_at`.

## 8. Métricas de Contexto Financiero

`obtener_contexto_financiero` debe separar siempre:

| Etiqueta | Fuente | Significado |
|---|---|---|
| `LIQUIDEZ_CUENTAS` | `sum(accounts.balance)` | Dinero actual en cuentas |
| `MES_ACTUAL(YYYY-MM)` | `obtener_balance_financiero(..., mes)` | Flujo del periodo actual |
| `PRESUPUESTOS_MES` | `obtener_presupuestos_v2(..., mes)` | Techos y gastado por categoría |
| `HISTORICO` | `obtener_balance_financiero(...)` sin mes | Flujo acumulado, no liquidez |
| `MOV_ACTUAL` | transacciones del periodo actual | Últimos movimientos relevantes |

Nunca presentar el neto histórico con la etiqueta genérica `Balance` ni compararlo con el total de presupuestos de un único mes.

## Compatibilidad Legacy

Aún existen colecciones legacy para migración/compatibilidad:

- `finanzas/`
- `presupuestos/`
- `metas/`
- `pagos_fijos/`
- `tareas/`

Las nuevas funciones deben escribir en Kebo. Los fallbacks legacy solo deben usarse cuando la estructura Kebo no tenga datos.

## Reglas de Seguridad

- No guardar tokens, contraseñas ni credenciales bancarias.
- `serviceAccountKey.json` debe permanecer fuera de Git y estar en `.gitignore`.
- Usar variables de entorno para credenciales (`FIREBASE_CREDENTIALS` o `FIREBASE_CREDENTIALS_PATH`).
- No borrar o migrar datos en producción sin script explícito, dry-run y confirmación.
