"""Audio transcription via Gemini."""
from google.genai import types

from modules.gemini.client import MODEL_NAME, _gemini_call_with_fallback

def transcribir_audio(ruta_audio: str) -> str:
    """Transcribe audio a texto usando Gemini (solo transcripción, sin análisis)."""
    try:
        # Subir el archivo
        audio_file = _gemini_call_with_fallback(lambda c: c.files.upload(file=ruta_audio))

        # Prompt simple para transcripción
        prompt_transcripcion = "Transcribe exactamente lo que se dice en este audio. Solo devuelve el texto transcrito, sin comentarios."

        # Obtener transcripción
        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt_transcripcion, audio_file],
                config=types.GenerateContentConfig(
                    max_output_tokens=500,
                    temperature=0.1,  # Bajo para precisión
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            ).text
        )

        # Limpiar el archivo
        try:
            audio_file.delete()
        except Exception:
            pass

        return response_text.strip() if response_text else ""
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return ""
