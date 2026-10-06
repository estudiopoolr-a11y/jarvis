# Integración del Widget Scriptable con Vercel

## 📱 Descripción General
El widget para iOS basado en **Scriptable** consume los datos financieros y de presupuestos directamente desde la API desplegada en Vercel.

## 🔗 Endpoint Consumido
- **URL**: `https://jarvis-two-pi-13.vercel.app/api/widget/dashboard`
- **Método**: `GET`
- **Parámetros opcionales**: `?usuario_id=default`

## 📊 Formato de Payload JSON Esperado
El endpoint responde con la siguiente estructura JSON normalizada:

```json
{
  "total_balance_cuentas": 1540000.0,
  "cuentas": [
    { "nombre": "Nu", "disponible": 500000.0 },
    { "nombre": "Nequi", "disponible": 840000.0 },
    { "nombre": "Efectivo", "disponible": 200000.0 }
  ],
  "mes": "Octubre 2026",
  "total_ingresos": 3200000.0,
  "total_gastos": 1660000.0,
  "presupuestos": [
    {
      "categoria": "Alimentación",
      "gastado": 450000.0,
      "limite": 600000.0,
      "excedido": false
    }
  ]
}
```

## 🛠️ Archivo del Widget
- **Ruta local**: `widgets/jarvis_widget.js`
- **Configuración BASE_URL**: `https://jarvis-two-pi-13.vercel.app`

## 🔗 Enlaces Wiki
- [[Jarvis/migracion_render_a_vercel.md]]
- [[Jarvis/resolucion_function_invocation_failed_vercel.md]]
- [[Jarvis/estado_proyecto.md]]
- [[FastAPI.md]]
- [[Vercel.md]]

> *Última actualización: 2026-10-06*
