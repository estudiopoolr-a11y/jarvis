# Módulo de Préstamos y Recordatorios

Este módulo gestiona la deuda externa (préstamos otorgados y recibidos) y la automatización de alertas de vencimiento.

## Arquitectura del Módulo

El módulo se divide en una capa de rutas API y un servicio de lógica de negocio.

### 1. Endpoints API (`[[app/routes/prestamos.py]]`)
- `POST /api/v1/prestamos/registrar`: Registra un nuevo préstamo.
- `POST /api/v1/prestamos/pagar`: Registra un pago parcial o total.
- `GET /api/v1/prestamos/listar`: Lista préstamos (filtra por pendientes).
- `DELETE /api/v1/prestamos/{id}`: Elimina un registro.
- `GET /api/v1/prestamos/por-cobrar`: Sumatoria total de capital pendiente.

### 2. Servicio de Alertas (`[[modules/reminders/service.py]]`)
- `verificar_prestamos_vencidos()`: Escanea la base de datos en busca de préstamos cuya `fecha_limite` sea menor o igual a hoy.
- Integrado con el sistema de recordatorios general para generar notificaciones vía Telegram.

## Esquemas de Datos (Pydantic)
- **PrestamoCreate**: `persona`, `monto`, `fecha_limite`, `nota`, `tipo` (prestado/prestado_a_mi).
- **PagoPrestamoCreate**: `prestamo_id`, `monto_pago`, `fecha`.

## Flujo de Trabajo
1. Registro de préstamo $\rightarrow$ Firestore (`loans` collection).
2. Ejecución diaria de `verificar_prestamos_vencidos` $\rightarrow$ Alerta en Telegram.
3. Registro de pago $\rightarrow$ Actualización de estado del préstamo.
