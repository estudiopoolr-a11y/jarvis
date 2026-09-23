"""Investment intent + ticker analysis."""
import yfinance as yf
from google.genai import types
from google.genai.errors import APIError

from modules.db import guardar_tarea, obtener_contexto_financiero
from modules.gemini.client import MODEL_NAME, SYSTEM_INSTRUCTION, _gemini_call_with_fallback
from modules.gemini.errors import _manejar_error_api, _manejar_error_generico

def _es_intencion_inversion(texto: str) -> bool:
    """Detecta si el usuario está preguntando sobre inversiones."""
    palabras = [
        "invertir", "inversion", "inverti", "cdt", "renta fija", "dónde meto",
        "plata", "tasas", "app", "broker", "banco", "ahorrar",
        "donde invierto", "fondo", "etf", "bolsa", "acciones",
        "rendimientos", "intereses", "deposito", "ahorro"
    ]
    return any(p in texto for p in palabras)


def _asesorar_inversion(prompt_usuario: str, usuario_id: str):
    """Genera asesoría de inversión para Colombia usando búsqueda web en tiempo real."""
    try:
        # Obtener datos financieros del usuario
        balance_neto, ingresos, gastos, _ = obtener_balance_financiero(usuario_id)

        # Calcular capacidad de inversión (20% del balance disponible, mínimo $100.000)
        capacidad_inversion = max(balance_neto * 0.20, 100000)

        # OPTIMIZADO: 1 sola llamada con todo incluido (antes 3 llamadas)
        prompt_unificado = f"""Eres JARVIS, asesor financiero ejecutivo de Colombia.

CONTEXTO: Balance=${balance_neto:,.0f} COP | Capacidad sugerida=${capacidad_inversion:,.0f} COP (20%)

PREGUNTA: {prompt_usuario}

INSTRUCCIONES (responde en español):
1. Busca en la web: tasas CDT Colombia {datetime.now().month}/{datetime.now().year} (Bancolombia, Davivienda, Banco de Bogotá)
2. Busca en la web: mejores apps invertir Colombia 2026 (Tyba, Trii, Hapi, Nequi)
3. Genera respuesta con: tabla tasas CDT | comparativa apps | recomendación personalizada
4. Finaliza con: TAREAS: [tarea1] | [tarea2] | [tarea3]

Si balance < $500.000, recomienda apps sin monto mínimo.
Si balance > $1.000.000, recomienda diversificar CDT + app."""

        response = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_unificado,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    max_output_tokens=2000
                )
            )
        )

        respuesta = response.text or "No se pudo generar la asesoría."

        # Extraer y crear tareas si existen
        if "TAREAS:" in respuesta:
            parte_tareas = respuesta.split("TAREAS:")[1].strip()
            # Tomar solo la primera línea de tareas
            parte_tareas = parte_tareas.split("\n")[0]
            tareas = [t.strip() for t in parte_tareas.split("|") if t.strip()]

            for tarea in tareas[:3]:  # Máximo 3 tareas
                if 5 < len(tarea) < 100:
                    guardar_tarea(usuario_id, tarea, "Media", "Esta semana")

        return respuesta

    except Exception as e:
        return f"⚠️ Error generando asesoría de inversión: {e}"


def analizar_inversion(ticker: str) -> str:
    """Analiza un activo bursátil combinando datos en vivo de yfinance y búsqueda web."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")

        datos_mercado = ""
        if not hist.empty:
            precio_actual = hist['Close'].iloc[-1]
            precio_anterior = hist['Close'].iloc[-2]
            cambio_pct = ((precio_actual - precio_anterior) / precio_anterior) * 100
            datos_mercado = f"Precio actual: ${precio_actual:,.2f} USD. Variación reciente: {cambio_pct:+.2f}%."
        else:
            datos_mercado = f"No se obtuvieron datos directos de yfinance para `{ticker}`."

        prompt_analisis = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            f"El usuario evalúa el activo o instrumento financiero: {ticker.upper()}.\n"
            f"Datos del mercado: {datos_mercado}\n"
            "Busca en la web el contexto reciente de este activo o empresa y realiza un análisis frío, objetivo y pragmático."
        )

        response_text = _gemini_call_with_fallback(
            lambda c: c.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_analisis,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    max_output_tokens=1500
                )
            ).text
        )
        return response_text or "Error analizando el activo."
    except APIError as e:
        return _manejar_error_api(e, contexto=f"análisis de {ticker}")
    except Exception as e:
        return _manejar_error_generico(e, contexto=f"análisis de {ticker}")
