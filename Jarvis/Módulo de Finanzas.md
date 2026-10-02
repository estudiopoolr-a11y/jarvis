# Módulo de Finanzas

Este módulo gestiona la lógica financiera del sistema Jarvis, incluyendo cuentas, transacciones, presupuestos y análisis financiero.

## Refactorización de Cuentas
Se realizó una refactorización en [[modules/finance/accounts.py]] para:
- Consultar directamente la colección raíz `accounts` en Firestore (sin subcolección `users`)
- Soportar mapeo bidireccional de campos:
  - Español: `nombre`, `tipo`
  - Inglés: `name`, `type`
- Mantener compatibilidad con el formato Kebo para integración con sistemas externos

## Gestión de Cuentas
El sistema gestiona tres cuentas principales mediante el script [[scripts/setup_three_accounts.py]]:
- **Nu** (tipo: `bank`) - Cuenta bancaria
- **Nequi** (tipo: `wallet`) - Billetera digital
- **Efectivo** (tipo: `cash`) - Dinero en efectivo

## Limpieza y Verificación
Se ejecutó el script [[scripts/check_cuenta_principal.py]] para:
- Verificar la ausencia de una cuenta llamada `cuenta_principal` en la colección raíz
- Confirmar que solo existen las tres cuentas esperadas (Nu, Nequi, Efectivo)
- Validar que la arquitectura sin anidación de usuarios está funcionando correctamente

## Normalización de Nombres
Para mejorar la flexibilidad de consulta, el sistema implementa normalización de texto en los nombres de cuentas y skills. Esta normalización:
- Convierte todo el texto a minúsculas
- Elimina acentos y diacríticos (ej: 'á' → 'a', 'ñ' → 'n')
- Elimina espacios extra y normaliza espacios múltiples a uno solo
- Permite búsquedas insensibles a mayúsculas, minúsculas y variaciones tipográficas

Ejemplos de equivalencia tras normalización:
- 'Nu' ≡ 'nu' ≡ 'NU'
- 'Nequi' ≡ 'nequi' ≡ 'NEQUI'
- 'Efectivo' ≡ 'efectivo' ≡ 'EFECTIVO'
- 'Presupuesto Madre' ≡ 'presupuesto madre' ≡ 'PRESUPUESTO MADRE'
- 'México' ≡ 'mexico' ≡ 'MÉXICO'

Esta mejora permite que usuarios se refieran a cuentas y skills usando variaciones naturales del lenguaje sin preocuparse por el formato exacto.

## Navegación
- [[Base de Datos Firestore]] - Detalles de la estructura de persistencia
- [[Mapa del Sistema]] - Volver al nodo central de documentación

---
## Gestión de Presupuestos y Transacciones
Se implementaron mejoras críticas en la lógica de presupuestos y el procesamiento de lenguaje natural (NLP):
- **Normalización Estricta de Categorías:** Se integró `_normalizar_cat_str` en [[modules/finance/categories.py]] y se aplicó en todas las operaciones CRUD de presupuestos ([[modules/finance/budgets/create.py]], [[modules/finance/budgets/update.py]], [[modules/finance/budgets/delete.py]]) para evitar duplicados por mayúsculas/minúsculas (ej. 'Madre' vs 'madre').
- **Priorización Temporal:** Se corrigió la lógica de parseo de presupuestos para que, si el usuario especifica un mes/año en el prompt, este tenga prioridad sobre la fecha actual del sistema.
- **Mejora en Registro de Gastos:** Se actualizaron los patrones de regex en [[modules/nlp/parsers/transacciones.py]] para capturar correctamente frases naturales como "Me gasté X en Y", asegurando que el registro de transacciones no falle por el uso de pronombres iniciales.

## Adaptación de Widget iPhone
Se actualizó el endpoint del dashboard en [[app/routes/widgets.py]] para alinearse con la nueva arquitectura de base de datos:
- Las consultas de cuentas ahora se realizan sobre la colección raíz `accounts` sin filtrado por usuario, obteniendo todas las cuentas disponibles (Nu, Nequi, Efectivo).
- El endpoint ya no depende de la ruta obsoleta `users/{user_id}/accounts`.
- Los parámetros de consulta como `usuario_id` son ahora opcionales y se usan solo para presupuestos y transacciones.

---
*Última actualización: 2026-10-02 - Normalización de categorías, corrección de NLP para gastos y actualización de endpoints del Widget.*