<!-- cSpell:disable -->
# 🤖 Proyecto JARVIS - Asistente Personal Inteligente

> **"Sistemas en línea. JARVIS v3.2 Operativo."**

Asistente personal integrado con inteligencia artificial (Gemini) y automatización para la gestión de tareas, finanzas y notas de voz. Diseñado para ser tu asistente ejecutivo personal, frío, analítico y eficiente. Desplegado 24/7 en Render con bot de Discord persistente.

---

## 📋 Tabla de Contenidos

1. [¿Qué es JARVIS?](#-qué-es-jarvis)
2. [Características Principales](#-características-principales)
3. [Arquitectura del Sistema](#-arquitectura-del-sistema)
4. [Estructura del Proyecto](#-estructura-del-proyecto)
5. [Inicio Rápido Local](#-inicio-rápido-local)
6. [Despliegue en Render 24/7](#-despliegue-en-render-247)
7. [Uso en Discord](#-uso-en-discord)
8. [Ejemplos de Mensajes](#-ejemplos-de-mensajes)
9. [Dashboard Web](#-dashboard-web)
10. [API REST](#-api-rest)
11. [Automatización (Cron Jobs)](#-automatización-cron-jobs)
12. [Alertas Proactivas](#-alertas-proactivas)
13. [Optimización y Arquitectura](#-optimización-y-arquitectura)
14. [Variables de Entorno](#-variables-de-entorno)
15. [Troubleshooting](#-troubleshooting)
16. [Historial de Cambios](#-historial-de-cambios)
17. [Roadmap](#-roadmap)
18. [Contribuir](#-contribuir)

---

## 🎯 ¿Qué es JARVIS?

JARVIS es un **asistente personal ejecutivo** que combina:
- 🤖 **IA Generativa** (Google Gemini) con rotación automática de API keys
- 💬 **Bot de Discord** persistente 24/7
- 💰 **Gestión financiera personal** (ingresos, gastos, presupuestos)
- 📋 **Gestión de tareas** con prioridades y fechas límite
- 🚨 **Alertas proactivas** automáticas vía Discord
- 📊 **Resúmenes diarios y semanales** automáticos
- 🌐 **Dashboard web** con visualización en tiempo real

Está diseñado para funcionar como un **mayordomo digital**: ejecuta tareas, monitorea tu salud financiera, te alerta sobre problemas y responde preguntas complejas sobre tus datos.

### ¿Por qué JARVIS?

| Problema                     | Solución de JARVIS                            |
| ---------------------------- | --------------------------------------------- |
| Perder el control de gastos  | Registro automático + detección de anomalías  |
| Olvidar tareas importantes   | Tareas con prioridad + alertas de vencimiento |
| Necesitar consultar finanzas | Balance en tiempo real + resúmenes            |
| Sobrecargar la API de Gemini | Parsers determinísticos (90% sin Gemini)      |
| Caídas del servicio          | Bot separado del web service en Render        |
| Rate limits (429)            | Rotación automática entre 5 API keys          |

---

## ✨ Características Principales (Actualizado v3.2)

### 🧩 Integración de Herramientas (Tools Calling)
- **Pydantic**: Validación estricta de esquemas de todas las funciones.
- **Google Calendar API**: CRUD completo para eventos en modo calendario.
- **Function Calling**: Gemini invoca herramientas (`ALL_TOOLS`) nativamente.
- **Finanzas Defensivas**: Parsing robusto, limpieza de datos y auditoría mensual.
- **Bot Discord inteligente**: Detección automática de DMs y notas de voz para procesamiento con herramientas.

### 💰 Gestión Financiera Inteligente
- **Registro automático de ingresos y gastos** a través de lenguaje natural
- **Carga masiva de datos** mediante prompt estructurado (presupuestos + transacciones en un solo mensaje)
- **Presupuestos por categoría** con alertas proactivas cuando se acercan al límite
- **Balance financiero en tiempo real** con ingresos, gastos y neto
- **Historial de transacciones** almacenado de forma segura en Firebase
- **Procesamiento de recibos** mediante IA (extrae monto, establecimiento y categoría)
- **Detección de gastos anormales** (gastos que superan 2x del promedio histórico)

### 📋 Gestión de Tareas
- **Creación de tareas** con prioridad (Alta/Media/Baja) y fecha límite
- **Lista de pendientes** siempre actualizada
- **Marcado de completado** mediante búsqueda inteligente
- **Detección de tareas vencidas** y próximas a vencer
- **Recordatorios contextuales** basados en tu carga de trabajo

### 🧠 Inteligencia Artificial Avanzada
- **Análisis de inversiones** combinando datos en vivo de Yahoo Finanzas y búsqueda web
- **Comprensión de lenguaje natural** para intenciones complejas
- **Fundamentación en datos reales**: la IA responde ÚNICAMENTE con información de tu base de datos
- **Modo voz** con respuesta de audio mediante Google Text-to-Speech
- **Rotación automática de hasta 5 API Keys de Gemini** (round-robin ante 429)

### 🖥️ Múltiples Interfaces
- **Discord Bot**: Comandos, menciones de usuario y menciones de rol (`<@&ID>`)
- **Dashboard Web**: Visualización en tiempo real con FastAPI
- **API REST**: Endpoints para integraciones externas
- **Procesamiento de multimedia**: Imágenes (recibos) y audio (notas de voz)
- **Notificaciones vía Webhook de Discord**: Resúmenes automáticos

### 🚨 Alertas Proactivas (Fase 3)
- **Presupuestos críticos** (>90% del límite)
- **Presupuestos en advertencia** (>80% del límite)
- **Tareas vencidas** con días de retraso
- **Tareas próximas a vencer** (≤2 días)
- **Gastos anormales** (>2x del promedio histórico)
- **Resumen semanal** cada domingo con comparación vs semana anterior

### 🔐 Privacidad y Seguridad
- **Datos almacenados exclusivamente en tu proyecto Firebase**
- **Ninguna información financiera se envía a terceros** excepto para Gemini
- **Variables de entorno** para credenciales sensibles
- **Safety settings configuradas** para evitar contenido inapropiado

---

## 🏗️ Arquitectura del Sistema
*(Ver README original para detalles del diagrama)*

## 📂 Estructura del Proyecto
*(Ver README original para detalles de la estructura)*

## 🚀 Inicio Rápido Local
*(Ver README original para instrucciones de instalación)*

## 💬 Uso en Discord
*(Ver README original para comandos)*

## 📨 Ejemplos de Mensajes
*(Ver README original para ejemplos)*

## 🌐 Dashboard Web
*(Ver README original para detalles)*

## 🔌 API REST
*(Ver README original para endpoints)*

## ⏰ Automatización (Cron Jobs)
*(Ver README original para automatización)*

## 🚨 Alertas Proactivas
*(Ver README original para alertas)*

## 🔧 Optimización y Arquitectura
*(Ver README original para optimización)*

## 🔑 Variables de Entorno
*(Ver README original para variables)*

## 🔍 Troubleshooting
*(Ver README original para troubleshooting)*

## 📈 Historial de Cambios
- **V3.2 (Septiembre 2026)**: Integración Pydantic + GCal + Tools + Discord Audio Listener.
- ... *(Mantener historial original)*

## 🚀 Roadmap
- ... *(Mantener roadmap original)*

---

## 🤝 Contribuir
*(Ver README original para contribución)*

## 📄 Licencia
*(Ver README original para licencia)*

## ☎️ Soporte
*(Ver README original para soporte)*

## 🙏 Agradecimientos
*(Ver README original para agradecimientos)*

---
*Hecho con ❤️ por tu asistente personal ejecutivo JARVIS*
> **"Sistemas en línea. A la espera de instrucciones."**
<!-- cSpell:enable -->
