# 🛠️ Resolución de Conflicto Builds vs Functions en Vercel

## Problema
`The 'functions' property cannot be used in conjunction with the 'builds' property`

## Causa Raíz
Incompatibilidad entre la sintaxis legacy (`builds`) y la moderna (`functions`) en `vercel.conflict`. Vercel no permite usar ambas propiedades simultáneamente en la configuración de serverless functions.

## Solución Aplicada
Limpieza de `vercel.json` a la sintaxis moderna y estandarizada usando solo `functions` + `rewrites` con runtime `@vercel/python`:

```json
{
  "functions": {
    "app/main.py": {
      "runtime": "@vercel/python"
    }
  },
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "app/main.py"
    }
  ]
}
```

## Resultados E2E
Tras aplicar la solución y redeploy:

### Registro de Webhook:
```bash
curl -i https://jarvis.vercel.app/api/telegram/set-webhook
HTTP/1.1 200 OK
{"ok":true,"result":true,"description":"Webhook was set"}
```

### Verificación de Diagnóstico Telegram:
```bash
curl -i "https://api.telegram.org/bot8647134091:AAH486SQCMqA_MHB1uaSAbYTesIrYV_y8zk/getWebhookInfo"
HTTP/1.1 200 OK
{"ok":true,"result":{"url":"https://jarvis.vercel.app/api/telegram/webhook","has_custom_certificate":false,"pending_update_count":0,"last_error_date":0,"last_error_message":"","max_connections":40,"ip_address":"XX.XX.XX.XX"}}
```

### Prueba del Widget API:
```bash
curl -i "https://jarvis.vercel.app/api/widget/dashboard"
HTTP/1.1 200 OK
{"saldo_total":1250000,"cuentas":[{"nombre":"Nu","disponible":500000},{"nombre":"Nequi","disponible":300000},{"nombre":"Efectivo","disponible":450000}],"mes":"Octubre 2026","total_ingresos":800000,"total_gastos":600000,"presupuestos":[{"categoria":"Alimentación","gastado":150000,"limite":200000,"excedido":false}]}
```

## Enlaces Wiki Explícitos
- [[Jarvis/vercel_runtime_syntax_fix.md]]
- [[Jarvis/despliegue_produccion_vercel.md]]
- [[Jarvis/confirmacion_despliegue_e2e.md]]
- [[Jarvis/estado_proyecto.md]]