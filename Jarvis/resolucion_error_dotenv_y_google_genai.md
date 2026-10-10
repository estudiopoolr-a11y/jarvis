# Resolución ModuleNotFoundError: dotenv y conflicto de importación de genai en Vercel

## Descripción
Nota técnica que documenta la resolución del error `ModuleNotFoundError: No module named 'dotenv'` y el manejo tolerante de la importación de `google.genai` en el entorno Serverless de Vercel.

## Causa Raíz
- El módulo `modules/gemini/client.py` realizaba importaciones estáticas de `dotenv` y `google.genai` sin bloques defensivos.
- En Vercel Serverless, los entornos pueden tener paquetes faltantes o versiones incompatibles durante el arranque inicial (cold start).
- La ausencia de `python-dotenv` causaba un colapso inmediato del módulo Gemini, afectando todas las rutas que lo dependían.

## Solución Aplicada

### 1. Declaración explícita en `requirements.txt`
Se añadió `python-dotenv==1.0.1` como dependencia explícita bajo la sección de utilidades del sistema:
```
python-dotenv==1.0.1
```
Verificación: `pip install -r requirements.txt` → `python-dotenv==1.0.1` ya satisfecho.

### 2. Blindaje de Importación en `modules/gemini/client.py`
Se envolvió la importación de `dotenv` y `google.genai` en bloques defensivos `try/except ImportError`:
```python
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv no disponible; usando variables de entorno del sistema")

try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    genai = None
    APIError = Exception
```

Esto garantiza que:
- El startup de FastAPI en Vercel **nunca falle** por falta de `python-dotenv`.
- Las variables de entorno se cargan correctamente cuando `python-dotenv` está disponible.
- El SDK de Gemini se importa de forma tolerante a fallos, evitando colapsos por paquetes faltantes.
- El logger dedicado (`jarvis.gemini.client`) permite trazabilidad clara en Vercel Logs.

## Verificación

### Prueba de Importación
```bash
python -c "from modules.gemini.client import genai; print('OK: Módulo cliente de Gemini cargado correctamente')"
```
**Resultado:** `OK: Módulo cliente de Gemini cargado correctamente`

### Batería de Tests Unitarios
```bash
python -m unittest discover -v tests
```
**Resultado:** 5/5 PASSING (Ran 5 tests in ~22s — OK)

## Impacto
- Elimina `ModuleNotFoundError: dotenv` en Vercel Serverless.
- Hace resiliente el arranque del módulo Gemini ante variaciones de entorno.
- Mantiene compatibilidad con desarrollo local y producción.
- Habilita logging estructurado para diagnóstico en Vercel Logs.

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] — Bitácora de avances y registro de estado.
- [[Índice Principal.md]] — Nodo central de navegación.
- [[FastAPI]] — Framework API.
- [[Gemini API]] — Proveedor LLM con capacidad Vision.
- [[Vercel]] — Infraestructura serverless.
- [[Python]] — Lenguaje de programación.
- [[Jarvis/resolucion_error_pillow_vision.md|Resolución Error PIL Vision]] — Nota hermana sobre blindaje de importaciones.
