# JARVIS

JARVIS is preparing to run the official OpenClaw Gateway on Koyeb, with
Telegram as its chat channel and Google Gemini as its model provider. The
existing FastAPI finance API and Vercel deployment remain separate; deploying
OpenClaw does not migrate those routes or automatically connect its tools to
Firebase or Notion.

## Deploy OpenClaw on Koyeb

1. Push this repository to GitHub and create a Koyeb service from the
   `main` branch. Select the Dockerfile builder and configure an HTTP service
   on container port `8080`.
2. Add these environment variables in the Koyeb service settings:
   - `OPENCLAW_GATEWAY_TOKEN`: a long, unique random secret.
   - `TELEGRAM_BOT_TOKEN`: the token from BotFather.
   - `GEMINI_API_KEY`: a Google AI Studio API key.
   - `KOYEB_PUBLIC_URL`: the exact HTTPS URL assigned to the Koyeb service,
     with no trailing slash.
3. Deploy. When GitHub auto-deploy is enabled for the service, pushes to the
   selected branch trigger new deployments.
4. Open the service URL and complete Telegram pairing. The Gateway UI uses
   token authentication.

If a custom tool/plugin is later configured for Firebase or Notion, add its
credentials separately in Koyeb: `FIREBASE_DATABASE_URL`,
`FIREBASE_CREDENTIALS`, `NOTION_API_KEY`, and `NOTION_FINANZAS_DB_ID`.

The Dockerfile uses the published OpenClaw image rather than installing this
repository as an npm package. `openclaw_config/config.json` contains the
Gateway's real configuration. Firebase and Notion credentials can be added as
Koyeb environment variables for future custom tools, but environment variables
alone do not implement or enable those integrations.

I cannot guarantee that a Koyeb deployment is currently free, needs no card,
or runs continuously: availability, sleep behavior, storage persistence,
resource limits, and payment-method requirements depend on the current plan
and account eligibility. Confirm these in the Koyeb dashboard before relying
on an always-on bot or storing durable Gateway state there. Koyeb may redeploy
the container without preserving its writable filesystem; a restart can
therefore require Telegram pairing again.

See [the Koyeb deployment note](Jarvis/despliegue_koyeb_openclaw_engine.md)
for the full setup and operational boundaries.

## Existing JARVIS API

The FastAPI application remains rooted at `app/main.py`, with its existing
Telegram webhook, finance routes, and widget API deployed separately through
Vercel. Run its tests with Python 3.12:

```bash
python -m unittest discover -v tests
```

Moving existing FastAPI behavior, finance tools, Firebase access, or
production Telegram webhooks into OpenClaw requires a separate integration
and cutover.

Tags: [[OpenClaw]] [[Koyeb]] [[Docker]] [[Gemini API]] [[Telegram]]
