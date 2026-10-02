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

## Navegación
- [[Base de Datos Firestore]] - Detalles de la estructura de persistencia
- [[Mapa del Sistema]] - Volver al nodo central de documentación

---
*Última actualización: 2026-10-02*