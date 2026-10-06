# 📜 Migración de Render a Vercel

## 🎯 Objetivo
Migrar el despliegue de JARVIS desde Render.com a Vercel para aprovechar la infraestructura serverless de Vercel, mejorar el rendimiento y reducir los costos de mantenimiento.

## 🔧 Cambios Realizados

### 1. Configuración de Vercel
- Actualización de `vercel.json` para usar el formato moderno con `functions` + `rewrites`
- Configuración de runtime `@vercel/python` en lugar de `python3.11`
- Definición de rutas para todos los endpoints necesarios:
  - `/api/(.*)` para rutas de API
  - `/widget/(.*)` para el widget de iOS
  - `/telegram/(.*)` para webhooks de Telegram
  - `/(.*)` para rutas de frontend

### 2. Eliminación de Configuración de Render
- Borrado de `Procfile` (configuración específica de Render)
- Eliminación de referencias a variables de entorno específicas de Render en `README.md` y código.
- Limpieza de comentarios y documentación que mencionaban Render.

### 3. Actualización de Documentación
- Creación de notas específicas para Vercel:
  - [[Jarvis/Vercel.md]]
  - [[Jarvis/despliegue_produccion_vercel.md]]
  - [[Jarvis/vercel_routing_fix.md]]
  - [[Jarvis/vercel_runtime_syntax_fix.md]]
  - [[Jarvis/resolucion_conflicto_vercel_builds.md]]
  - [[Jarvis/integracion_widget_scriptable_vercel.md]]
- Actualización de [[Jarvis/telegram_bot_webhook.md]] para reflejar el nuevo endpoint en Vercel
- Actualización de [[Jarvis/monitoreo_uptimerobot.md]] para health checks en Vercel

### 4. Verificación de Despliegue
- Pruebas E2E confirmando que todos los endpoints funcionan correctamente:
  - `/api/widget/dashboard` retorna datos financieros
  - `/api/telegram/set-webhook` configura el webhook de Telegram
  - `/debug` proporciona información de diagnóstico
- Confirmación de que el webhook de Telegram apunta correctamente a Vercel

## 📊 Comparación Render vs Vercel

| Característica | Render | Vercel |
|----------------|--------|--------|
| Tipo de Servicio | Web Service | Serverless Functions |
| Escalado Automático | Sí (con límites) | Sí (instantáneo) |
| Tiempo de Arranque | ~500ms (cold start) | ~100ms (edge optimized) |
| Límite de Tiempo | 15 min (background workers) | 10 sec (serverless functions) |
| Persistencia de Sistema de Archivos | Efímero (reinicia con deploy) | Efímero (requiere almacenamiento externo) |
| Variables de Entorno | Panel de Render | Panel de Vercel |
| Health Checks | Manual | Integrado con UptimeRobot |
| Costos (Plan Gratuito) | 750 horas/mes | 100 GB-Horas/mes |

## ⚠️ Consideraciones Importantes

### 1. Funciones Serverless
- Las funciones en Vercel tienen un límite de ejecución de 10 segundos
- Los procesos de larga duración deben ser redesignados o movidos a background tasks externos
- Los cron jobs se manejan mediante Vercel Cron Jobs (en lugar de Render Cron Jobs)

### 2. Persistencia de Estado
- El sistema de archivos es efímero en Vercel
- Se requiere almacenamiento externo para:
  - Base de datos (Firestore ya se usa)
  - Memoria episódica (ChromaDB requiere disco persistente o migración a solución cloud)
  - Caches temporales

### 3. Variables de Entorno
- Todas las variables de entorno deben configurarse en el panel de Vercel
- Las variables críticas incluyen:
  - `FIREBASE_CREDENTIALS` o `FIREBASE_SERVICE_ACCOUNT`
  - `TELEGRAM_BOT_TOKEN`
  - `DISCORD_BOT_TOKEN` (si se usa)
  - `GEMINI_API_KEY`

## 🔗 Enlaces Relacionados
- [[Vercel]] - Información general sobre la plataforma
- [[FastAPI]] - Framework usado para el backend
- [[Telegram API]] - Integración de webhooks
- [[despliegue_produccion_vercel.md]] - Guía detallada de despliegue
- [[vercel_routing_fix.md]] - Solución de problemas de routing
- [[vercel_runtime_syntax_fix.md]] - Corrección de sintaxis de runtime
- [[resolucion_conflicto_vercel_builds.md]] - Resolución de conflictos en vercel.json
- [[telegram_bot_webhook.md]] - Configuración del webhook de Telegram
- [[monitoreo_uptimerobot.md]] - Monitoreo de health checks
- [[Jarvis/integracion_widget_scriptable_vercel.md]] - Integración con Scriptable

## ✅ Estado Actual
- [x] Migración completada y verificada
- [x] Desmantelamiento total de Render (eliminación de referencias y archivos obsoletos)
- [x] Todos los endpoints funcionando correctamente en Vercel
- [x] Webhook de Telegram apuntando a Vercel
- [x] Widget de iOS (Scriptable) reconectado exitosamente a Vercel (`/api/widget/dashboard`)
- [x] Despliegues automáticos mediante Git push a Vercel

## 📝 Próximos Pasos
- [ ] Evaluar solución persistente para ChromaDB en Vercel (posible migración a Pinecone o similar)
- [ ] Implementar sistema de colas para tareas de larga duración
- [ ] Optimizar funciones serverless para reducir tiempo de ejecución
- [ ] Configurar monitoreo avanzado con Vercel Analytics
- [ ] Documentar procedimientos de rollback y recuperación de desastres

> *Última actualización: 2026-10-06*
> *Desmantelamiento de Render y estabilización de Scriptable Widget completados.*
