---
name: integracion_widget_scriptable_vercel
description: Documentación técnica de la conexión entre el Widget de Scriptable (iOS) y el backend de JARVIS en Vercel.
type: project
category: tech_stack
keywords:
  - "Vercel"
  - "Scriptable"
  - "FastAPI"
  - "iOS Widget"
  - "JSON Payload"
usage_scenarios:
  - "Depuración de datos del widget de iOS"
  - "Actualización de endpoints de la API de widgets"
  - "Modificación de la interfaz visual del widget"
---

# Integración Widget Scriptable $\rightarrow$ Vercel

Este documento detalla la configuración y el flujo de datos entre el script de JavaScript ejecutado en la app **Scriptable (iOS)** y el servidor de **JARVIS en Vercel**.

## 🛠️ Configuración de Conexión

El widget consume datos mediante peticiones HTTP GET hacia el servidor serverless de Vercel.

- **URL Base:** `https://jarvis-two-pi-13.vercel.app`
- **Endpoint de Consumo:** `/api/widgets/resumen`
- **Script Local:** `widgets/jarvis_widget.js`

## 📡 Flujo de Datos (Payload JSON)

El backend FastAPI procesa la solicitud y devuelve un objeto JSON optimizado para la renderización en iOS.

### Ejemplo de Respuesta Exitosa
```json
{
  "status": "ok",
  "total_balance_cuentas": 1500.50,
  "cuentas": [
    {"nombre": "Bancolombia", "saldo": 1000.00},
    {"nombre": "Efectivo", "saldo": 500.50}
  ],
  "mes": "2026-10",
  "total_ingresos": 3000.00,
  "total_gastos": 1200.00,
  "presupuestos": [
    {"categoria": "Comida", "limite": 500, "gastado": 300}
  ],
  "mensaje": "JARVIS Vercel Active"
}
```

### Blindaje Defensivo (Fallback)
En caso de error en la base de datos o timeout de Vercel, el endpoint está blindado para devolver un payload válido que evite el cierre inesperado del widget:
```json
{
  "status": "ok",
  "total_balance_cuentas": 0,
  "cuentas": [],
  "mes": "Error",
  "total_ingresos": 0,
  "total_gastos": 0,
  "presupuestos": [],
  "mensaje": "JARVIS Vercel Active (Fallback)"
}
```

## 🔗 Enlaces Relacionados
- [[Jarvis/migracion_render_a_vercel.md]]
- [[Jarvis/resolucion_function_invocation_failed_vercel.md]]
- [[Jarvis/estado_proyecto.md]]
