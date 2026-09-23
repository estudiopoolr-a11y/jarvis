"""modules/gemini/vision.py - Procesamiento de imágenes con Gemini Vision.

Gemini solo LEE la imagen y devuelve texto. Cualquier mutación de Firestore
(registrar el gasto de una factura) la hace el router determinístico de
`modules.nlp`, nunca este módulo.
"""
import re

from PIL import Image

from modules.gemini.client import MODEL_NAME, SYSTEM_INSTRUCTION, _gemini_call_with_fallback


def procesar_imagen(ruta_imagen: str, prompt: str) -> str:
    """Envía una imagen a Gemini Vision y retorna la respuesta.
    
    Args:
        ruta_imagen: Ruta local al archivo de imagen.
        prompt: Instrucción o pregunta sobre la imagen.
        
    Returns:
        Respuesta de Gemini Vision como string.
    """
    
    def _call(client):
        img = Image.open(ruta_imagen)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, img],
            config={"system_instruction": SYSTEM_INSTRUCTION}
        )
        return response.text

    return _gemini_call_with_fallback(_call)


def extraer_total_factura(ruta_imagen: str) -> str:
    """Extrae el total de una factura desde una imagen.

    Args:
        ruta_imagen: Ruta local al archivo de imagen de la factura.

    Returns:
        String con el total extraído o mensaje de error.
    """
    prompt = """Analiza esta imagen de una factura o recibo.
    Extrae el monto TOTAL de la factura.
    Responde SOLO con el número del total, sin símbolos de moneda ni texto adicional.
    Si no puedes identificar el total, responde 'NO_ENCONTRADO'."""

    return procesar_imagen(ruta_imagen, prompt)


def analizar_factura(ruta_imagen: str) -> dict | None:
    """Lee una factura y devuelve monto, comercio y categoría sugerida.

    Solo lectura: no registra nada. Devuelve None si la imagen no es legible
    como factura. El monto se normaliza a entero en pesos (sin separadores).
    """
    prompt = (
        "Analiza esta imagen. Si es una factura, recibo o comprobante de pago, "
        "responde EXACTAMENTE en este formato, una línea por campo:\n"
        "MONTO: <total pagado, solo dígitos sin puntos ni comas>\n"
        "COMERCIO: <nombre del establecimiento, o 'desconocido'>\n"
        "CATEGORIA: <una de: Alimentación, Transporte, Servicios, Salud, "
        "Educación, Entretenimiento, Hogar, Otros>\n"
        "Si NO es una factura o no logras leer el total, responde exactamente: NO_FACTURA"
    )
    respuesta = (procesar_imagen(ruta_imagen, prompt) or "").strip()
    if not respuesta or "NO_FACTURA" in respuesta.upper():
        return None

    monto = re.search(r"MONTO:\s*\$?\s*([\d.,]+)", respuesta, re.IGNORECASE)
    if not monto:
        return None
    digitos = re.sub(r"[^\d]", "", monto.group(1))
    if not digitos:
        return None

    comercio = re.search(r"COMERCIO:\s*(.+)", respuesta, re.IGNORECASE)
    categoria = re.search(r"CATEGORIA:\s*(.+)", respuesta, re.IGNORECASE)
    return {
        "monto": int(digitos),
        "comercio": (comercio.group(1).strip() if comercio else "desconocido"),
        "categoria": (categoria.group(1).strip() if categoria else "Otros"),
    }


def extraer_texto_imagen(ruta_imagen: str) -> str:
    """Extrae texto o código de una imagen (OCR).
    
    Args:
        ruta_imagen: Ruta local al archivo de imagen.
        
    Returns:
        Texto extraído de la imagen.
    """
    prompt = """Extrae todo el texto visible en esta imagen.
    Si es código de programación, mantenlo formateado correctamente.
    Si es texto de una pantalla o tablero, transcríbelo fielmente."""
    
    return procesar_imagen(ruta_imagen, prompt)
