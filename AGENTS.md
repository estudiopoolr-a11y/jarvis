# AGENTS.md — JARVIS

## Repo facts
- **Remote:** `https://github.com/estudiopoolr-a11y/jarvis.git` (branch `main`)
- **Python:** 3.12 (pinned in `.python-version`)
- **Deploy:** Vercel serverless — Zero‑Config. `vercel.json` must only contain `env` and `rewrites`. **Never** add a `builds` or `functions` block.
- **Root entrypoint:** `app/main.py` (FastAPI, title `"JARVIS Backend"`, v2). All routes are included here.

## Commands
```bash
# Install deps (use Python 3.12)
pip install -r requirements.txt

# Run tests
python -m unittest discover -v tests

# Local dev (if a server.py exists)
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Architecture notes
- **Atomic Design** in `app/core/`: atoms → molecules → organisms → templates → routes.
- `app/routes/telegram.py` uses `resolver_llamada_segura()` (inspect‑based sync/async wrapper) — any new route handler must use it when calling mixed‑signature functions.
- Telegram webhook URL: `https://jarvis-two-pi-13.vercel.app/api/telegram/webhook`
- Register/reset webhook: `python scripts/register_telegram_webhook.py` (sets `drop_pending_updates=true`).
- Health check: `GET /api/telegram/health`
- Widget dashboard: `GET /api/widget/dashboard?usuario_id=default`
- Kebo finance CRUD: `app/routes/kebo/` (accounts, budgets, transactions, reports, export, seed).

## Environment variables
Required (set in Vercel dashboard + local `.env`):
- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY` (or `GEMINI_API_KEYS` comma‑separated)
- `FIREBASE_CREDENTIALS` (JSON string of service account key)

Optional: `HERMES_STORAGE_PATH`, `PORT`, `VERCEL_URL`, `DISCORD_WEBHOOK_URL`

`.env` is gitignored. Never commit secrets.

## Gotchas
- **requirements.txt:** No inline comments. `//` or `#` after a package line breaks `pip install`. Use clean lines only.
- **Pillow:** Pin `>=11.0.0` for Python 3.14 compatibility. `==10.4.0` will fail to build from source.
- **firebase-admin:** Required by the finance module; depends on `httpx>=0.28.1`. Bumping httpx may shift transitive deps.
- **Windows PowerShell:** Set `$env:PYTHONIOENCODING="utf-8"` before running scripts that print emojis (register_telegram_webhook.py, test scripts).
- **Git lock files:** `.git/index.lock` may persist after crashes; remove it before committing: `Remove-Item .git/index.lock -Force`.
- **LF→CRLF warnings:** Files with LF line endings trigger git warnings on Windows. This is expected; do not change core editor settings.

## Docs workflow (.clinerules)
All code changes must be documented in Obsidian notes under `Jarvis/`. The canonical index is `Jarvis/Índice Principal.md`. Update `Jarvis/estado_proyecto.md` with date, change summary, and wiki links after every session. New architectural notes must be linked from the index.
