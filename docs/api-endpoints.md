# 🌐 API Endpoints (FastAPI)

## Fuentes

- **Definición de rutas**: `app/routes/` (paquete; `app/routes/kebo/` para endpoints Kebo)
- **Lógica de negocio**: `app/services/*`, `modules/db.py`
- **App principal**: `app/main.py` importado por `server.py`

---

## Rutas Principales

| Método | Ruta | Descripción |
|---|---|---|
| GET/HEAD | `/` | Healthcheck (keepalive para UptimeRobot) |
| GET/HEAD | `/dashboard` | Dashboard HTML con Chart.js |
| GET | `/dashboard/v1` | Dashboard legacy (compatibilidad) |
| POST | `/api/comando` | Ejecuta intención natural desde web |
| GET | `/api/finanzas/resumen` | Resumen financiero JSON |
| GET | `/api/finanzas/presupuestos?mes=YYYY-MM` | Presupuestos del mes |
| GET | `/api/kebo/export-pdf` | Exporta reporte mensual a PDF |
| GET | `/health` | Healthcheck alternativo |

> **Nota**: Algunos endpoints pueden haber cambiado. Verifica en `app/routes.py` antes de usar.

---

## Ejemplo: Dashboard v1

```python
# app/routes.py:get_datos_dashboard_v1()
return {
    "balance": 561991,
    "ingresos": 3862707,
    "gastos": 3300716,
    "presupuestos": {
        "Casa": 150000,
        "Mamá": 150000,
        "Deudas": 205000
    },
    "tareas": [
        {"tarea": "...", "prioridad": "Media", "fecha_limite": "..."}
    ]
}
```

---

## Mantenimiento

1. ¿Endpoint nuevo? Agrega su ruta a esta tabla
2. ¿Respuesta cambiada? Actualiza el ejemplo JSON
3. ¿Ruta eliminada? Mueve a sección "Legacy" con nota de deprecated

**Última actualización**: 2026-09-17 (v3.2)
