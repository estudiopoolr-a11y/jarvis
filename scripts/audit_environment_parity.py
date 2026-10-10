import importlib  # Importar módulo importlib para carga dinámica de paquetes #
import sys  # Importar módulo sys para inspección de versión del intérprete #


def auditar_entorno_python():  # Función para auditar la paridad del entorno #
  print(
      f"[PASO 1/3] Evaluando versión de Python activa: {sys.version}",
      flush=True,
  )  # Imprimir versión activa #

  dependencias_criticas = [  # Definir lista de paquetes fundamentales del sistema #
      "fastapi",  # Framework web principal #
      "uvicorn",  # Servidor ASGI #
      "httpx",  # Cliente HTTP asíncrono #
      "PIL",  # Librería Pillow para imágenes #
      "yfinance",  # Consultas financieras de mercado #
      "google.generativeai",  # SDK de Gemini API #
  ]  # Cierre de lista de dependencias #

  print(
      "[PASO 2/3] Verificando presencia de dependencias en requirements.txt...",
      flush=True,
  )  # Imprimir paso 2 #
  for pkg in dependencias_criticas:  # Iterar sobre cada paquete de la lista #
    try:  # Iniciar bloque defensivo de importación #
      importlib.import_module(pkg)  # Intentar importar el módulo dinámicamente #
      print(f"   [OK] Módulo '{pkg}' disponible y cargado", flush=True)  # Éxito #
    except ImportError as e:  # Capturar falla de importación #
      print(
          f"   [FALTANTE] Módulo '{pkg}' no encontrado: {e}", flush=True
      )  # Error #

  print(
      "[PASO 3/3] Probando carga del Core FastAPI (app.main)...", flush=True
  )  # Imprimir paso 3 #
  try:  # Iniciar bloque de prueba del entrypoint #
    sys.path.insert(0, '.')
    import app.main  # Importar el punto de entrada principal de la aplicación #

    print(
        "   [OK] Core 'app.main' cargado sin errores de sintaxis ni de importación",
        flush=True,
    )  # Éxito #
  except Exception as e:  # Capturar falla en el startup #
    print(
        f"   [CRITICO] Error al importar 'app.main': {e}", flush=True
    )  # Error crítico #


if __name__ == "__main__":  # Punto de entrada principal #
  auditar_entorno_python()  # Ejecutar la función de auditoría #