# Consolidación de Vercel Serverless

## Arquitectura activa

JARVIS mantiene su backend en [[FastAPI]] (`app/main.py`) y su despliegue
Serverless en [[Vercel]]. El bot de [[Telegram]] procesa primero la intención
con el router determinístico y accede a datos financieros reales mediante
[[Firebase]]/Firestore. [[Gemini API]] se usa para interpretación y respuestas
generativas cuando corresponde.

`vercel.json` conserva `version: 2` y `PYTHONUNBUFFERED=1`. Se mantiene el
enrutamiento Zero-Config existente: no añadir `builds`, `functions` ni rutas
manuales, que ya causaron conflictos con el descubrimiento de FastAPI. El
runtime Python se fija con `.python-version` y las dependencias se declaran en
`requirements.txt`. Véase [[Jarvis/arquitectura_paridad_python_y_vercel]].

## Análisis consciente

`modules/ai.py` expone `analizar_solicitud_consciente(texto, historial=None)`,
función asíncrona que delega la solicitud a `google-genai` mediante el cliente
compartido y su mecanismo de rotación de claves. Devuelve un objeto con
`intencion` (`CONSULTAR_FINANZAS`, `GESTIONAR_TAREAS` o `CONSULTA_GENERAL`)
y `parametros` extraídos del texto. Un historial opcional aporta contexto
conversacional.

La función clasifica solicitudes: no ejecuta escrituras de finanzas, no
reemplaza `analizar_intencion_mensaje` ni el router determinístico actual del
webhook. Los errores de credenciales/API y respuestas no válidas se propagan
para no presentarlos como resultados exitosos.

## Configuración y verificación

Define `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY` o `GEMINI_API_KEYS`, y
`FIREBASE_CREDENTIALS` como variables protegidas en Vercel. En local, usa una
copia ignorada de `.env.example`.

```bash
python -m unittest discover -v tests
```

La prueba enfocada del nuevo analizador cubre la extracción estructurada,
entradas vacías y respuestas no JSON. Las pruebas de integración existentes
para el webhook y el router siguen cubriendo el flujo de
[[Telegram]]/[[Firebase]].

Etiquetas: [[FastAPI]] [[Vercel]] [[Gemini API]] [[Firebase]] [[Python]]
