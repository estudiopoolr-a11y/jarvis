# JARVIS

JARVIS está migrando su motor conversacional persistente al Gateway de
OpenClaw en una VPS Ubuntu de Oracle Cloud Always Free. La API financiera
FastAPI y el despliegue actual en Vercel continúan disponibles; este Compose
no migra automáticamente esas rutas ni conecta Firebase o Notion.

## OpenClaw en Oracle Cloud

Instala Docker Engine y el plugin Compose v2 en la VPS:

```bash
git clone https://github.com/estudiopoolr-a11y/jarvis.git
cd jarvis
sudo bash scripts/setup_oracle_vps.sh
```

Crea el archivo local de entorno:

```bash
cp .env.example .env
openssl rand -hex 32
```

Guarda el valor generado en `.env` como `OPENCLAW_GATEWAY_TOKEN` y completa
las credenciales de Telegram y Gemini. Firebase y Notion se pasan al
contenedor para integraciones personalizadas, pero no activan esas
integraciones por sí solos. No subas `.env` a Git.

El script agrega el usuario al grupo `docker`; cierra la sesión SSH y vuelve
a conectarte para aplicar el cambio. Luego prepara los directorios
persistentes, valida Compose e inicia el Gateway:

```bash
mkdir -p openclaw_config data
sudo chown -R 1000:1000 openclaw_config data
docker compose config
docker compose up -d
docker compose ps
```

El Gateway escucha en el puerto interno `18789` y solo se publica en la
interfaz loopback de la VPS. Para abrir su UI de control desde una estación de
trabajo, crea un túnel SSH:

```bash
ssh -L 18789:127.0.0.1:18789 ubuntu@IP_DE_LA_VPS
```

Abre `http://127.0.0.1:18789/` y autentícate con `OPENCLAW_GATEWAY_TOKEN`.
No expongas directamente el puerto `18789` a Internet. Para un endpoint HTTPS
público, configura por separado un proxy inverso y TLS, y permite HTTPS tanto
en el firewall del host como en las reglas de red de Oracle Cloud.

OpenClaw usa long polling de Telegram por defecto. Una vez configurado
`TELEGRAM_BOT_TOKEN`, envía un mensaje al bot y aprueba la solicitud de pairing:

```bash
docker compose exec openclaw-gateway node dist/index.js pairing list telegram
docker compose exec openclaw-gateway node dist/index.js pairing approve telegram CODIGO
```

El estado persistente y los datos del workspace se guardan en
`openclaw_config/` y `data/`. Consulta la
[nota de arquitectura de Oracle Cloud](Jarvis/arquitectura_openclaw_oracle_cloud.md)
para conocer los límites de despliegue y detalles operativos.

## API JARVIS existente

La aplicación FastAPI continúa en `app/main.py`. Mantiene las rutas de
webhook Telegram, finanzas y widget desplegadas actualmente en Vercel. Ejecuta
sus pruebas con Python 3.12:

```bash
python -m unittest discover -v tests
```

El contenedor OpenClaw es un despliegue independiente; trasladar el
comportamiento FastAPI, las herramientas financieras, el acceso a Firebase o
los webhooks de producción de Telegram requiere una integración y una
migración explícitas.
