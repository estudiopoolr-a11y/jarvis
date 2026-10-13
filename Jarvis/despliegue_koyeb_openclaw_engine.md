# Despliegue de OpenClaw Engine en Koyeb

## Alcance

Esta arquitectura ejecuta la imagen oficial de [[OpenClaw]] en Koyeb con
[[Docker]], usa [[Gemini API]] como proveedor de modelo y configura
[[Telegram]] como canal. La API FastAPI y sus integraciones financieras
continúan aparte en Vercel hasta realizar una migración específica.

## Imagen y configuración

El `Dockerfile` tiene una etapa pequeña que comprueba que
`openclaw_config/config.json` sea JSON válido y una etapa de runtime basada en
`ghcr.io/openclaw/openclaw:latest`. La imagen publicada ya contiene
OpenClaw y sus dependencias; no se intenta instalar el repositorio JARVIS
como paquete npm ni invocar un `npm start` inexistente.

El Gateway escucha en `0.0.0.0:8080` dentro del contenedor para que el proxy
de Koyeb pueda acceder. La UI exige `OPENCLAW_GATEWAY_TOKEN`. Su origen
permitido debe ser la URL HTTPS exacta de la aplicación, configurada en
`KOYEB_PUBLIC_URL`. Los mensajes directos de Telegram usan la política
predeterminada de pairing; los remitentes desconocidos deben aprobarse desde
OpenClaw.

El proveedor se configura con el formato oficial `google/<modelo>` y lee la
clave desde `GEMINI_API_KEY`. El ejemplo selecciona
`google/gemini-3.1-pro-preview`; verifica en el catálogo de OpenClaw y en
Google AI Studio que el modelo y el acceso estén habilitados para tu cuenta.
Los nombres y el esquema `agent.provider`/`integrations` de la propuesta
original no son campos válidos de configuración del Gateway y no se usan.

Firebase y Notion no se activan por definir variables de entorno. Requieren
plugins o herramientas personalizadas compatibles con el esquema de OpenClaw;
no deben añadirse campos arbitrarios a `openclaw_config/config.json`, porque
OpenClaw rechaza configuraciones que no validan.

## Configurar un servicio desde GitHub

1. Envía los cambios a la rama GitHub que utilizará el servicio.
2. En Koyeb, crea un servicio nuevo desde el repositorio GitHub y selecciona
   el builder **Dockerfile** en la raíz.
3. Configura el puerto HTTP del servicio como `8080` y el comando de inicio
   predeterminado del contenedor.
4. Define las variables sensibles en el panel de Koyeb:
   - `OPENCLAW_GATEWAY_TOKEN`: genera un secreto fuerte, por ejemplo con
     `openssl rand -hex 32`.
   - `TELEGRAM_BOT_TOKEN`: token de BotFather.
   - `GEMINI_API_KEY`: clave de Google AI Studio.
   - `KOYEB_PUBLIC_URL`: URL HTTPS exacta asignada al servicio, sin `/` final.
5. Despliega y confirma en los logs que el Gateway inicia sin errores de
   configuración. Si corriges `KOYEB_PUBLIC_URL`, vuelve a desplegar o
   reiniciar para que OpenClaw cargue el origen correcto.
6. Abre la URL del servicio, autentícate con el token y completa el pairing
   del primer chat privado de Telegram.
7. Habilita en Koyeb el despliegue automático para la rama elegida. Cada
   `git push` a esa rama crea una nueva versión del servicio.

Los nombres exactos de los botones del panel pueden cambiar. La disponibilidad
de instancias gratuitas, el requisito de tarjeta, límites de memoria,
políticas de suspensión y persistencia de volúmenes dependen de las condiciones
vigentes de Koyeb y de la elegibilidad de la cuenta. Verifica esos puntos en
el dashboard antes de desplegar: no se puede garantizar que actualmente haya
una instancia gratuita sin tarjeta o con ejecución continua. No se debe
prometer 24/7 ni almacenamiento persistente sin confirmar el plan.

Si una herramienta personalizada requiere Firebase o Notion, agrega sus
credenciales en variables Koyeb (`FIREBASE_DATABASE_URL`,
`FIREBASE_CREDENTIALS`, `NOTION_API_KEY`, `NOTION_FINANZAS_DB_ID`) y configura
el plugin correspondiente por separado. Las variables por sí solas no
implementan esas integraciones.

## Persistencia y operación

El `openclaw.json` se incluye en la imagen al construir, pero la sesión,
pairing y demás estado escrito en `/home/node/.openclaw` residen en el
filesystem del contenedor si no se configura un volumen persistente compatible
con el plan. Una reconstrucción o reemplazo de instancia puede perder ese
estado y requerir pairing de nuevo. No incluyas tokens ni claves dentro de
esta nota, el repositorio, el Dockerfile o la configuración JSON.

Referencias oficiales:

- [Docker de OpenClaw](https://docs.openclaw.ai/install/docker)
- [Configuración de Gemini para OpenClaw](https://docs.openclaw.ai/providers/google)
- [Variables de entorno de OpenClaw](https://docs.openclaw.ai/gateway/configuration/environment-variables)
- [Precios de Koyeb](https://www.koyeb.com/pricing)

Etiquetas: [[OpenClaw]] [[Koyeb]] [[Docker]] [[Gemini API]] [[Telegram]]
