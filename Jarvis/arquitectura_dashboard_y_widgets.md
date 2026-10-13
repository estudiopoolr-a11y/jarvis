# Arquitectura de datos del dashboard y los widgets

La vista web (`/dashboard`), las estadísticas (`/api/finanzas/resumen`) y las
rutas de widgets (`/api/widget/resumen` y `/api/widget/dashboard`) usan
`modules/finance/dashboard.py` como fuente común. La ruta de datos del widget
está registrada junto con las vistas y estadísticas en el entrypoint
[[app/main.py]] de [[FastAPI]] y también en la aplicación API heredada.

El agregado consulta las colecciones activas de [[Firebase]]/Firestore para
el mes solicitado: `transactions/{YYYY-MM}/items`,
`budgets/{YYYY-MM}/items`, `categories` y `accounts`. Las transacciones
aceptan `type`/`amount` (Kebo) y `tipo`/`monto` (compatibilidad anterior),
normalizando `income`/`ingreso` y `expense`/`gasto`. Los presupuestos del mes
se complementan con los límites configurados en categorías cuando no hay
presupuestos mensuales.

El resumen devuelve balance neto del mes, ingresos, gastos, presupuesto y
porcentaje utilizado, además del balance actual agregado de las cuentas y el
detalle por categoría. Las rutas no devuelven cifras simuladas ni éxitos con
valores cero cuando una lectura falla; responden con HTTP 500 para que la
interfaz distinga datos ausentes de errores de Firebase.

El widget Scriptable usa la ruta singular `/api/widget/resumen`. El alias
`/api/widget/dashboard` se conserva para clientes existentes.

Etiquetas: [[Firebase]] [[Firestore]] [[FastAPI]] [[Dashboard]] [[Python]]
