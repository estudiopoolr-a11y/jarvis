"""Cliente NVIDIA NIM con rotación automática de API keys."""
import os  # Importar os para leer variables de entorno del sistema
import random  # Importar random para rotación aleatoria de claves
import logging  # Importar logging para auditoría de errores en Vercel

import httpx  # Importar httpx para solicitudes HTTP asíncronas seguras

logger = logging.getLogger("jarvis.nvidia")  # Logger exclusivo para el subsistema NVIDIA

# URL oficial del endpoint compatible OpenAI de NVIDIA NIM
_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
# Modelo por defecto (Llama 3.1 70B Instruct)
_NIM_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")

# Pool de claves — se carga perezosamente para evitar inicialización prematura
_API_KEYS: list[str] = []


def _load_keys() -> None:
    """Cargar el pool de claves NVIDIA desde variables de entorno."""
    global _API_KEYS
    if _API_KEYS:  # Ya cargadas, no repetir
        return
    keys_str = os.getenv("NVIDIA_API_KEYS", os.getenv("NVIDIA_API_KEY", ""))
    if not keys_str:
        _API_KEYS = []
        logger.warning("No hay NVIDIA_API_KEYS configuradas en el entorno.")
        return
    _API_KEYS = [k.strip() for k in keys_str.split(",") if k.strip()]
    logger.info("Pool NVIDIA cargado: %d clave(s) disponible(s).", len(_API_KEYS))


def obtener_claves_nvidia() -> list[str]:
    """Retorna el pool de claves NVIDIA cargadas."""
    _load_keys()
    return list(_API_KEYS)


async def pensar_respuesta_nvidia(prompt: str) -> str:
    """
    Consulta NVIDIA NIM con rotación automática de claves.
    Intenta cada clave del pool si hay rate-limit (429/503).
    Retorna texto generado o mensaje de fallback si todas fallan.
    """
    _load_keys()
    if not _API_KEYS:
        raise ValueError("No hay claves de NVIDIA API configuradas en el entorno.")

    # Rotar (barajar) las claves para distribuir carga
    claves_rotadas = list(_API_KEYS)
    random.shuffle(claves_rotadas)

    ultimo_error: str | None = None

    for api_key in claves_rotadas:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": _NIM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "max_tokens": 1024,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(_NIM_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    contenido = data["choices"][0]["message"]["content"].strip()
                    logger.info("Respuesta NVIDIA generada exitosamente.")
                    return contenido

                if response.status_code in (429, 503):
                    logger.warning(
                        "Clave NVIDIA agotada/ocupada (status %d), rotando clave…",
                        response.status_code,
                    )
                    continue

                logger.error("Error HTTP NVIDIA %d: %s", response.status_code, response.text)
                ultimo_error = response.text

        except Exception as exc:
            logger.error("Excepción al conectar con NVIDIA API: %s", exc)
            ultimo_error = str(exc)

    # Todas las claves fallaron
    logger.error("Todas las claves NVIDIA fallaron. Último error: %s", ultimo_error)
    return (
        "⚠️ Los servicios de IA (NVIDIA y Gemini) se encuentran temporalmente saturados. "
        "Por favor, intenta de nuevo en unos momentos."
    )
