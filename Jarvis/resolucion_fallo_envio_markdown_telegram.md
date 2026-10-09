# Resolución de fallo de envío Markdown en Telegram

Fecha: 2026-10-09

## Causa raíz
Telegram API rechaza mensajes con formato Markdown malformado o entidades no soportadas, devolviendo 400 Bad Request. El despacho anterior no reintentaba, provocando descartes silenciosos y percepción de fallo en el usuario.

## Solución implementada
`despachar_respuesta_telegram` en `app/routes/telegram.py` ahora ejecuta doble fallback:
1. **Intento 1**: `sendMessage` con `parse_mode="Markdown"`.
2. **Intento 2**: Si status_code != 200, reintento inmediato con payload en texto plano sin `parse_mode`.

Logging explícito de ambos intentos y confirmación de entrega.

## Validación
- Suite de pruebas 5/5 PASSING.
- Script `scripts/test_envio_directo.py` verifica sintaxis y flujo de despacho.
- Webhook sigue devolviendo siempre 200 OK a Telegram.

## Enlaces Wiki
[[Jarvis/estado_proyecto.md]]
[[Índice Principal.md]]
[[FastAPI]]
[[Vercel]]
[[Atomic Design]]
