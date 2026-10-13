# Estructura Financiera 2026 en Firebase Firestore

Creada el **2026-10-13** a partir de la directiva de migración e indexación de datos financieros 2026. El script [`scripts/seed_finanzas_2026.py`](../scripts/seed_finanzas_2026.py) ingesta ingresos, gastos por categoría y loans en el esquema raíz que consumen el dashboard y los widgets.

## Colecciones raíz escritas

### `transactions/{YYYY-MM}/items`
Transacciones mensuales. Cada mes recibe **1 documento de ingreso** (`type: "income"`, `category_name: "Ingresos"`) y **N documentos de gasto** (`type: "expense"`, `category_name` = nombre de categoría). Campos comunes: `amount`, `category_name`, `description`, `date`, `created_at`.

| Mes   | Ingresos (COP) | Gastos (COP) | # Docs |
|-------|----------------|--------------|--------|
| 2026-05 | 1.061.159,03 | 713.000,00 | 9 |
| 2026-06 | 1.058.894,26 | 616.500,00 | 7 |
| 2026-07 | 936.455,00 | 1.094.775,69 | 8 |
| 2026-08 | 806.199,03 | 876.440,00 | 6 |

**Total ingresos:** 3.862.707,32 COP.

### `categories`
Catálogo de 12 categorías con `nombre`, `budget` (0,0 — límites no definidos), `tipo: "variable"`, `icono` y `color`:

Moto 🏍️ `#8b5cf6` · Madre 👩 `#ec4899` · Padre 👨 `#0ea5e9` · Deudas 💳 `#ef4444` · Alimentación 🍎 `#22c55e` · Fútbol ⚽ `#10b981` · Gym 🏋️ `#f59e0b` · Use personal 💸 `#3b82f6` · Gastos tontos 😅 `#6b7280` · Women 👗 `#d946ef` · Ahorro 🐷 `#84cc16` · Préstamos 🤝 `#f97316` · Otros 📦 `#475569`.

### `loans`
7 documentos con `persona`, `monto`, `monto_original`, `monto_pagado: 0.0`, `monto_pendiente`, `fecha`, `status: "pendiente"`, `pagos: []`. Acumulado: **232.500,00 COP**.

| Fecha     | Persona              | Monto (COP) |
|-----------|----------------------|-------------|
| 2026-08-24 | Jhostyn            | 40.000,00 |
| 2026-08-24 | Mamá pañales Saló   | 20.000,00 |
| 2026-07-31 | Brother             | 50.000,00 |
| 2026-07-31 | Cinemark            | 32.500,00 |
| 2026-07-31 | Váscula             | 50.000,00 |
| 2026-07-21 | Brother             | 20.000,00 |
| 2026-07-21 | Brother             | 20.000,00 |

### `finanzas/2026`
Nodo resumen con el esquema de la directiva: `ingresos` (por mes + `total_ingresos`), `gastos_por categoría` (por mes con `total` y `categoria`), `prestamos_detalle` (`acumulado_total` + `transacciones`).

## Idempotencia
- Transacciones: `_mes_tiene_items()` salta meses que ya tienen documentos.
- Categorías: `_crearyCategoriaSiFalta()` no duplica por `nombre`.
- Préstamos: se omite si existe `(persona, fecha, monto)` idéntico.

## Consumo
- [`modules/finance/dashboard.py`](../modules/finance/dashboard.py) → `obtener_resumen_dashboard(mes=)` lee `categories`, `transactions/{mes}/items`, `budgets/{mes}/items`, `accounts`.
- [`modules/finance/loans.py`](../modules/finance/loans.py) → colección `loans`.
- Endpoints: `/api/finanzas/resumen`, `/api/widget/resumen`, `/api/widget/dashboard`.

## Limitaciones conocidas
- **Presupuestos:** no se recibieron límites, así que `porcentaje_uso` / `porcentaje` son `0.0` hasta que se creen docs en `budgets/{YYYY-MM}/items`.
- **Mes por defecto:** el dashboard muestra el mes actual (2026-10). Los datos de mayo–agosto son visibles pasando `?mes=2026-07` o `mes="2026-07"` en la llamada.
- **Agosto 2026:** el desglose literal suma 527.540,00 COP; el resto (348.900,00) se registró como categoría `Otros` para cumplir el total de 876.440,00 COP declarado.

Tags: [[Firebase]] [[Python]] [[Dashboard]] [[Finanzas]]