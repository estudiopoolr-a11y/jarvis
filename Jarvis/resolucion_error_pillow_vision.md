# Resolución ModuleNotFoundError: PIL en Gemini Vision

## Descripción
Nota técnica que documenta la resolución del error `ModuleNotFoundError: No module named 'PIL'` en Vercel Serverless al cargar el módulo de visión `modules/gemini/vision.py`, y el blindaje de importación para arranque resiliente.

## Causa Raíz
- Vercel Logs reportaban: `ModuleNotFoundError: No module named 'PIL'` al importar `modules.gemini.vision` en el startup de la función serverless.
- La librería `Pillow` (que provee el paquete `PIL`) no estaba declarada en `requirements.txt`.
- La importación estática `from PIL import Image` colapsaba el arranque y cualquier ruta que importara transitivamente el módulo de visión.

## Solución Aplicada

### 1. Declaración en `requirements.txt`
Se añadió bajo la sección **Procesamiento de imágenes (Gemini Vision)**:
```plaintext
Pillow>=10.0.0  # Librería PIL para procesamiento de imágenes en el módulo Gemini Vision #
```
Verificación: `pip install -r requirements.txt` → `Pillow>=10.0.0` ya satisfecho (12.3.0).

### 2. Blindaje de Importación en `modules/gemini/vision.py`
Se envolvió la importación en un bloque defensivo `try/except ImportError`:
```python
try:  # Iniciar bloque defensivo para carga opcional de la librería Pillow
    from PIL import Image  # Importar clase Image para procesamiento de imágenes
except ImportError:  # Capturar excepción si la librería PIL/Pillow no está instalada
    Image = None  # Asignar valor nulo de respaldo para evitar caída del sistema
```

### 3. Guard Degradado en `procesar_imagen`
Se agregó una validación temprana para retornar mensaje controlado si la librería no está disponible:
```python
def procesar_imagen(ruta_imagen: str, prompt: str) -> str:
    if Image is None:  # Validar presencia de la librería Pillow en el runtime
        return "⚠️ Módulo de imagen no disponible (Pillow ausente). Intenta de nuevo en modo texto."
    # ... resto de la función
```

Esto garantiza que:
- El startup de FastAPI en Vercel **nunca falle** por falta de Pillow.
- Las consultas de texto plano (NLP, finanzas, Telegram) sigan operativas aunque la visión falle.
- El usuario reciba un mensaje claro de degradación en lugar de un error 500 opaco.

## Verificación

### Prueba de Importación
```bash
python -c "import app.main; from modules.gemini.vision import Image; print('✓ Módulo de visión e importación de app.main verificados con éxito')"
```
**Resultado:** `✓ Módulo de visión e importación de app.main verificados con éxito`

### Batería de Tests Unitarios
```bash
python -m unittest discover -v tests
```
**Resultado:** 5/5 PASSING (Ran 5 tests in ~36s — OK)

## Impacto
- Elimina `ModuleNotFoundError: PIL` en Vercel Serverless.
- Habilita procesamiento de imágenes con Gemini Vision como feature opcional.
- Mantiene resiliencia: texto plano, NLP, finanzas, Telegram operativos sin Pillow.
- Compatible con desarrollo local y producción.

## Enlaces Wiki
- [[Jarvis/estado_proyecto.md]] — Bitácora de avances y registro de estado.
- [[Índice Principal.md]] — Nodo central de navegación.
- [[FastAPI]] — Framework API.
- [[Gemini API]] — Proveedor LLM con capacidad Vision.
- [[Vercel]] — Infraestructura serverless.
- [[Python]] — Lenguaje de programación.