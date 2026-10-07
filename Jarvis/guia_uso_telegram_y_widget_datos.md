---
name: guia_uso_telegram_y_widget_datos
description: Guía de usuario y técnica para la interacción con JARVIS vía Telegram Bot y Widget de Scriptable con datos reales.
type: guide
category: usage
keywords:
  - "Telegram Bot"
  - "Scriptable Widget"
  - "Finanzas"
  - "Comandos"
  - "Vercel"
---

# 🤖 Guía de Uso: Telegram Bot & Widget de Datos Reales

Esta guía detalla el funcionamiento operativo de las dos interfaces principales de acceso rápido a JARVIS en producción.

## 📱 Widget de Scriptable (iOS)

El widget ahora consume datos dinámicos desde el endpoint `[[Jarvis/integracion_widget_scriptable_vercel.md]]` en Vercel.

### 📊 Indicadores Financieros
- **Saldo Total**: Muestra la suma consolidada de todas las cuentas registradas en Firestore.
- **Presupuesto Mensual**: Calcula la suma de los límites de todas las categorías de presupuesto del mes actual.
- **Porcentaje de Uso**: `(Gastos Totales del Mes / Presupuesto Total) * 100`.
- **Semáforo de Alerta**:
    - 🟢 **Verde**: Uso < 80% del presupuesto.
    - 🟡 **Amarillo**: Uso entre 80% y 95%.
    - 🔴 **Rojo**: Uso > 95% o excedido.
- **Modo Offline**: Si no hay conexión, el widget utiliza el último caché local almacenado en Scriptable para evitar pantallas vacías.

---

## ✈️ Telegram Bot

El bot opera mediante un webhook configurado en `[[Jarvis/telegram_bot_webhook.md]]`.

### 🛠️ Comandos Interactivos
| Comando | Acción | Descripción |
| :--- | :--- | :--- |
| `/start` | Inicio | Presenta el bot y despliega el menú de ayuda. |
| `/ayuda` | Ayuda | Lista todos los comandos disponibles. |
| `/balance` | Consulta | Retorna el saldo actual y el resumen financiero consolidado. |
| `/resumen` | Consulta | Alias de `/balance`. |
| `/gasto <monto> <cat>` | Registro | Registra una transacción rápidamente (Ej: `/gasto 15000 comida`). |

### 🧠 Interacción en Lenguaje Natural
Cualquier mensaje que no sea un comando es enviado al motor de IA (`[[Hermes Agent]]`). Puedes preguntar cosas como:
- *"¿Cuánto he gastado en transporte este mes?"*
- *"¿Me queda presupuesto para salir el fin de semana?"*
- *"Analiza mis gastos de la última semana."*

---

## 🔗 Enlaces Relacionados
- [[Jarvis/integracion_widget_scriptable_vercel.md]] - Detalles técnicos del Widget.
- [[Jarvis/telegram_bot_webhook.md]] - Arquitectura del Webhook de Telegram.
- [[Jarvis/estado_proyecto.md]] - Bitácora de estado general.
