# Entry point para Vercel Python Serverless
# Este archivo permite que Vercel despliegue la aplicación correctamente

from app.main import app  # Importar la aplicación FastAPI principal

# Vercel necesita esta variable 'app' para ejecutar la función serverless
application = app
