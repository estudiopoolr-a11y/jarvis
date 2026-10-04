# 🐛 Fix de Runtime en vercel.json

> Corrección del error `Function Runtimes must have a valid version` en Vercel.

---

## 📋 Resumen del Problema

| Ítem | Detalle |
|------|---------|
| **Error** | `Function Runtimes must have a valid version` |
| **Plataforma** | [[Vercel]] |
| **Archivo afectado** | `vercel.json` |
| **Fecha** | 2026-10-04 |
| **Causa** | Uso de `"runtime": "python3.11"` dentro de `functions` — formato no soportado por Vercel para Python Serverless. |

---

## 🔧 Solución Aplicada

### Antes (incorrecto)
```json
{
    "version": 2,
    "functions": {
        "app/main.py": {
            "runtime": "python3.11"  // ❌ Valor inválido
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

### Después (correcto)
```json
{
    "version": 2,
    "builds": [
        {
            "src": "app/main.py",
            "use": "@vercel/python"  // ✅ Build oficial de Vercel
        }
    ],
    "functions": {
        "app/main.py": {
            "runtime": "@vercel/python"  // ✅ Runtime válido
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

### ¿Por qué funciona?
- Vercel requiere que el `runtime` en `functions` sea una de las [runtimes oficiales](https://vercel.com/docs/runtimes), no versiones arbitrarias como `"python3.11"`.
- El valor correcto es `"@vercel/python"` (paquete oficial de Vercel para funciones Python).
- Se mantiene la sección `builds` para compatibilidad y claridad explícita.

---

## ✅ Verificación Post-Fix

1. **Despliegue exitoso en Vercel** (tras `git push`):
   - Build completado sin warnings de *Build Settings*.
   - Estado de despliegue: **Ready** en el panel de Vercel.

2. **Endpoints operativos**:
   ```bash
   $ curl -i https://jarvis.vercel.app/api/widget/dashboard
   HTTP/1.1 200 OK
   {"saldo_total": 1250000, "cuentas": [...]}  # Ejemplo de respuesta

   $ curl -i https://jarvis.vercel.app/api/telegram/set-webhook
   HTTP/1.1 200 OK
   {"ok":true,"result":true,"description":"Webhook was set"}
   ```

3. **Widget iPhone (Scriptable)**:
   - Recibe y renderiza correctamente los datos del endpoint `/api/widget/dashboard`.
   - Maneja errores de red mostrando mensaje amigable en caso de fallo.

---

## 📎 Referencias

- [[Jarvis/despliegue_produccion_vercel.md]] — Verificación E2E completa del despliegue.
- [[Jarvis/Vercel.md]] — Infraestructura serverless general en Vercel.
- [[Jarvis/estado_proyecto.md]] — Bitácora del proyecto con registro de esta corrección.
- [[.clinerules]] — Reglas globales de desarrollo y documentación en Obsidian.
