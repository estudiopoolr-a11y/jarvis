# Estrategia de Inversión

Este módulo implementa la lógica financiera avanzada para la gestión de metas, inversiones y planificación patrimonial dentro del sistema Jarvis.

## Cálculo del Balance Consolidado
El sistema calcula el balance financiero total mediante la suma de:
- **Nu**: Cuenta bancaria principal
- **Nequi**: Billetera digital
- **Efectivo**: Dinero en efectivo disponible

Este balance consolidado se obtiene consultando la colección raíz `accounts` en [[Base de Datos Firestore]] y se utiliza como base para todas las proyecciones y recomendaciones financieras.

## Proyección de Deudas vs. Ingresos
El módulo analiza:
- **Flujos de ingresos recurrentes** (salarios, ingresos pasivos, etc.)
- **Obligaciones de deuda** (tarjetas de crédito, préstamos, etc.)
- **Horizonte temporal** para proyectar la evolución del patrimonio neto

Estos cálculos permiten generar escenarios futuros y evaluar la sostenibilidad financiera a medio y largo plazo.

## Módulo de Metas Financieras
Implementa un sistema para:
- **Definir metas** (ahorro para viaje, fondo de emergencia, inversión, etc.)
- **Seguimiento automático** del progreso hacia cada meta
- **Recomendaciones de asignación** óptima de recursos basado en:
    - Tiempo disponible para alcanzar la meta
    - Tolerancia al riesgo del usuario
    - Condiciones del mercado actual
    - Balance consolidado y flujo de caja disponible

## Integración con el Módulo de Finanzas
Este módulo se basa en los datos procesados por [[Módulo de Finanzas]]:
- Utiliza las cuentas y transacciones validadas
- Aprovecha los presupuestos y categorías existentes
- Se integra con el sistema de recordatorios para metas temporales

## Navegación
- [[Módulo de Finanzas]] - Base de datos de cuentas y transacciones.
- [[Mapa del Sistema]] - Volver al nodo central de documentación.

---

## Estado de Implementación

- [x] **PASO 4 Completado**: Las herramientas `obtener_balance_consolidado` y `generar_recomendaciones_inversion` han sido implementadas en `src/agent/tools.py`.
- [x] **Pruebas validadas**: El script `scripts/test_balance_inversion.py` verifica correctamente el cálculo del balance consolidado (Nu + Nequi + Efectivo) y la generación de recomendaciones según los rangos de balance.
- [x] **Integración con Hermes Agent**: Las herramientas están registradas en `ALL_TOOLS` y disponibles para el motor ReAct del agente.

49 | *Última actualización: 2026-10-02*