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
*Última actualización: 2026-10-02 - Se agregó documentación sobre la normalización de nombres de cuentas y skills para mejorar la flexibilidad de consulta.*