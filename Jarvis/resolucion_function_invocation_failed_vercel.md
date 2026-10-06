# Resolución FUNCTION_INVOCATION_FAILED en Vercel

* **Síntoma Diagnosticado**: Error `FUNCTION_INVOCATION_FAILED` arrojado por Vercel Serverless.
* **Causa Raíz**: Colapso en tiempo de ejecución durante la carga de módulos e importaciones al iniciar la función serverless, agravado si uno de esos módulos importaba componentes pesados de IA durante el primer golpe de frío (cold start).
* **Solución Implementada**: Exportación explícita ASGI en formato resistente a roturas (lazy loading local), importaciones perezosas (lazy imports) de la capa `modules.ai` directo dentro del procesador del POST para evitar cargarla en memoria durante el importado estático de APIRouter, y blindaje total de excepciones respondiendo con HTTP `200 OK` en el webhook para calmar a Telegram y prevenir que desactive la URL.
* **Enlaces Wiki Explícitos**: [[Jarvis/telegram_bot_webhook.md]], [[Jarvis/configuracion_paso_a_paso_telegram_vercel.md]] y [[Jarvis/estado_proyecto.md]].
