# Arquitectura OpenClaw en Oracle Cloud

## Objetivo

Desplegar el Gateway de [[OpenClaw]] de forma persistente en una instancia
Ubuntu de [[Oracle Cloud]] Always Free, usando [[Docker]] Compose y conservando
el estado en disco. La integración conversacional usa [[Telegram]]; las claves
de [[Firebase]] y Notion se inyectan como entorno para herramientas propias.

## Topología y límites

- `docker-compose.yml` ejecuta la imagen oficial
  `ghcr.io/openclaw/openclaw:latest`. El Gateway escucha internamente en
  `18789`; el puerto del host se publica en `127.0.0.1` y no debe exponerse
  directamente a Internet.
- `openclaw_config/` conserva configuración y estado; `data/` conserva el
  workspace del agente. Ambos directorios deben ser escribibles por el
  usuario `node` del contenedor (UID 1000).
- `OPENCLAW_GATEWAY_TOKEN` es obligatorio para autenticar la UI. Generar un
  valor aleatorio con `openssl rand -hex 32` y guardarlo únicamente en `.env`.
- El bot Telegram usa `TELEGRAM_BOT_TOKEN` y long polling por defecto. Los
  mensajes directos desconocidos requieren aprobación de pairing.
- `GEMINI_API_KEY`, `FIREBASE_DATABASE_URL`, `FIREBASE_CREDENTIALS`,
  `NOTION_API_KEY` y `NOTION_FINANZAS_DB_ID` se pasan al contenedor. La
  presencia de Firebase/Notion en el entorno no instala plugins ni enlaza
  automáticamente las herramientas financieras existentes.
- La API FastAPI actual y sus rutas de finanzas/widget siguen desplegadas
  aparte en [[Vercel]]. Este Compose no las migra ni cambia su webhook de
  producción.

## Aprovisionamiento

En una instancia Ubuntu, desde la raíz clonada del repositorio:

```bash
sudo bash scripts/setup_oracle_vps.sh
cp .env.example .env
```

Completar `.env`, crear el token del Gateway y preparar volúmenes:

```bash
openssl rand -hex 32
mkdir -p openclaw_config data
sudo chown -R 1000:1000 openclaw_config data
docker compose config
docker compose up -d
docker compose ps
```

El script instala Docker Engine, Compose v2 y UFW. Permite SSH y HTTPS para
administración/reverse proxy, pero no abre el puerto del Gateway. Las reglas
de ingreso de [[Oracle Cloud]] se configuran aparte en el VCN/NSG. Para la UI,
usar un túnel SSH:

```bash
ssh -L 18789:127.0.0.1:18789 ubuntu@IP_DE_LA_VPS
```

Abrir `http://127.0.0.1:18789/` localmente e ingresar el token configurado.
No publicar el Gateway sin autenticación, TLS y configuración de origen
permitido.

## Telegram y operación

Con `TELEGRAM_BOT_TOKEN` cargado, enviar un mensaje al bot y aprobar la
solicitud de pairing desde el contenedor:

```bash
docker compose exec openclaw-gateway node dist/index.js pairing list telegram
docker compose exec openclaw-gateway node dist/index.js pairing approve telegram CODIGO
```

Consultar el estado con `docker compose ps` y los registros con
`docker compose logs -f openclaw-gateway`. Reiniciar con
`docker compose restart openclaw-gateway`. No incluir `.env`, credenciales ni
archivos de configuración con secretos en Git.

## Referencias

- [Docker de OpenClaw](https://docs.openclaw.ai/install/docker)
- [Configuración Telegram de OpenClaw](https://docs.openclaw.ai/channels/telegram/setup)
- [Seguridad del Gateway](https://docs.openclaw.ai/gateway/security)

Etiquetas: [[OpenClaw]] [[Oracle Cloud]] [[Docker]] [[Telegram]] [[Firebase]]
