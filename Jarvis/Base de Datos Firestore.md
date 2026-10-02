# Base de Datos Firestore

Esta nota describe la estructura de persistencia de datos utilizada en el proyecto Jarvis mediante Google Cloud Firestore.

## Estructura de Datos
El sistema utiliza un modelo de **colecciones raíz directas** para optimizar el acceso y simplificar la gestión de datos.

### Colecciones Principales
- `accounts`: Almacena la información de las cuentas financieras. Tras proceso de deduplicación, gestiona exactamente:
    - **Nu** (tipo: bank)
    - **Nequi** (tipo: wallet)
    - **Efectivo** (tipo: cash)
- `skills`: (Futura colección) Destinada a almacenar las capacidades y configuraciones de las habilidades del agente.

## Navegación
- [[Mapa del Sistema]] - Volver al nodo central.

---
*Última actualización: 2026-10-02 - Tras ejecución de scripts/deduplicate_accounts.py, se eliminaron 4 cuentas duplicadas dejando solo las canónicas: Nu, Nequi y Efectivo.*