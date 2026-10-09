# Resolución Error de Startup: yfinance ModuleNotFoundError

Fecha: 2026-10-09

## Causa del fallo
Vercel Logs reportaban:
```
ModuleNotFoundError: No module named 'yfinance'
```
Al iniciar la aplicación FastAPI, la importación estática en `modules/gemini/inversion.py` colapsaba el startup de Vercel porque `yfinance` no estaba declarado en `requirements.txt`.

## Solución aplicada
1. **requirements.txt**
   - Se añadió: `yfinance>=0.2.38  # Librería para consulta de cotizaciones y datos financieros bursátiles`
   - Verificación: `pip install -r requirements.txt` sin conflictos.

2. **Blindaje de importaciones**
   - `modules/gemini/inversion.py` ahora importa de forma opcional:
     ```python
     try:
         import yfinance as yf
     except ImportError:
         yf = None
     ```
   - `analizar_inversion` verifica `yf is None` y devuelve mensaje degradado en lugar de romper el proceso.
   - La app arranca de forma resiliente aunque el paquete no esté presente en runtime.

3. **Validación de startup**
   - `python -c "import app.main; print('✓ Servidor FastAPI cargado sin errores de startup')"`
   - `python -c "from app.api import api_router; print(f'✓ Total de rutas montadas: {len(api_router.routes)}')"`
   - Ambas verificaciones OK.

## Impacto
- Elimina colapso de startup en Vercel Serverless.
- Habilita consultas bursátiles opcionales con yfinance sin bloquear el resto del sistema.
- Mantiene compatibilidad con desarrollo local y producción.

## Enlaces Wiki
[[Jarvis/estado_proyecto.md]]
[[Índice Principal.md]]
[[FastAPI]]
[[Vercel]]
[[Python]]
