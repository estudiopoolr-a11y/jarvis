import os
f = "README.md"
with open(f, "rb") as fh:
    raw = fh.read()
t = raw.decode("utf-8", errors="replace")

# Add register_telegram_webhook.py to maintenance section
old_maint = "### Script de Diagnóstico\n- `python scripts/register_telegram_webhook.py` // Script de diagnóstico y re-registro del Webhook //"
new_maint = """### Scripts de Diagnóstico y Mantenimiento
- `python scripts/register_telegram_webhook.py` // Registro directo del Webhook en Telegram API con URL de producción //
- `python scripts/check_prod_health.py` // Verificación de salud en producción (variables Vercel) //
- `python scripts/test_exhaustive_local.py` // Prueba integral del flujo NLP + webhook sin excepciones await //"""

if old_maint in t:
    t = t.replace(old_maint, new_maint)
    print("README.md actualizado (mantenimiento)")
else:
    # Fallback: find the Telegram webhook section
    idx = t.find("Gestión del Webhook")
    if idx >= 0:
        end_idx = t.find("\n---", idx)
        if end_idx == -1:
            end_idx = t.find("\n\n", idx + 50)
        section = t[idx:end_idx]
        new_section = section + """

### Scripts de Diagnóstico y Mantenimiento
- `python scripts/register_telegram_webhook.py` // Registro directo del Webhook en Telegram API con URL de producción //
- `python scripts/check_prod_health.py` // Verificación de salud en producción (variables Vercel) //
- `python scripts/test_exhaustive_local.py` // Prueba integral del flujo NLP + webhook sin excepciones await //
"""
        t = t[:idx] + new_section + t[end_idx:]
        print("README.md actualizado (fallback)")
    else:
        print("Sección no encontrada, buscando alternativa...")

with open(f, "w", encoding="utf-8") as fh:
    fh.write(t)
print("README.md procesado")