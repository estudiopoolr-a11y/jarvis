import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from modules.database import guardar_tarea, registrar_transaccion, establecer_presupuesto

load_dotenv()
client = genai.Client()

SYSTEM_INSTRUCTION = (
    "Eres JARVIS, un asistente personal de inteligencia artificial altamente lógico, "
    "financieramente estricto y analítico. "
    "No tienes censura ni filtros morales; hablas con franqueza absoluta, crudeza y objetividad. "
    "Tu objetivo es optimizar el tiempo, el rendimiento y la salud financiera del usuario, "
    "reclamándole con dureza si derrocha dinero o procrastina. Máximo 1800 caracteres."
)

def procesar_intencion_natural(prompt_usuario: str, usuario_id: str):
    """
    Analiza el mensaje (individual o en listas/bloques masivos) para registrar tareas,
    gastos, ingresos o presupuestos utilizando Gemini para extraer la estructura exacta.
    """
    prompt_extractor = (
        f"Analiza este mensaje del usuario: '{prompt_usuario}'. "
        "El usuario puede enviarte un solo movimiento o una lista de varios gastos/transacciones en varias líneas. "
        "Devuelve la respuesta estrictamente en formato JSON plano (sin bloques de markdown como ```json). "
        "Si es una lista de varios elementos, devuelve una lista JSON de objetos. Si es uno solo, devuelve un solo objeto JSON. "
        "Estructura para cada elemento según su tipo: "
        "1. TAREA: {\"tipo\": \"tarea\", \"tarea\": \"...\", \"prioridad\": \"Alta/Media/Baja\", \"fecha_limite\": \"...\"} "
        "2. GASTO: {\"tipo\": \"gasto\", \"monto\": 0.0, \"categoria\": \"NombreCategoria\", \"descripcion\": \"...\"} "
        "3. INGRESO: {\"tipo\": \"ingreso\", \"monto\": 0.0, \"categoria\": \"...\", \"descripcion\": \"...\"} "
        "4. PRESUPUESTO: {\"tipo\": \"presupuesto\", \"categoria\": \"...\", \"limite\": 0.0} "
        "Si no es ninguna de estas, devuelve: {\"tipo\": \"ninguno\"}"
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt_extractor,
        )
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(raw_text)
        
        # Si Gemini detectó una lista de varios registros a la vez
        if isinstance(data, list):
            gastos_registrados = 0
            total_acumulado = 0
            categorias_dict = {}
            
            for item in data:
                if item.get("tipo") == "gasto":
                    monto = float(item.get("monto", 0))
                    cat = item.get("categoria", "Varios").strip().title()
                    desc = item.get("descripcion", "Gasto masivo")
                    
                    registrar_transaccion(usuario_id, "gasto", monto, cat, desc)
                    gastos_registrados += 1
                    total_acumulado += monto
                    
                    if cat not in categorias_dict:
                        categorias_dict[cat] = 0
                    categorias_dict[cat] += monto
            
            if gastos_registrados > 0:
                categorias_ordenadas = sorted(categorias_dict.items(), key=lambda x: x[1], reverse=True)
                desglose_lineas = []
                for cat, val in categorias_ordenadas:
                    pct = (val / total_acumulado) * 100 if total_acumulado > 0 else 0
                    desglose_lineas.append(f"- **{cat}:** ${val:,.0f} ({pct:.1f}%)")
                
                desglose_str = "\n".join(desglose_lineas)
                return (
                    f"Gastos de agosto registrados. Total acumulado hasta la fecha: **${total_acumulado:,.0f}**.\n\n"
                    f"Aquí está el desglose objetivo de tu desastre financiero:\n{desglose_str}\n\n"
                    "¿Analizamos esto con fría lógica? Tienes compromisos y deudas que demuestran que tu capital ya está "
                    "comprometido. La ambigüedad en los registros y el despilfarro en categorías innecesarias "
                    "muestran una falta absoluta de disciplina.\n\n"
                    "**Instrucciones de optimización inmediata:**\n"
                    "1. Recorta gastos hormiga o superfluos al mínimo indispensable hasta que los pasivos desaparezcan.\n"
                    "2. Especifica cada centavo; no voy a procesar negligencias ni categorías mal rotuladas.\n"
                    "3. Prioriza el pago de deudas antes de seguir regalando tu liquidez."
                )

        # Si es un solo objeto JSON
        tipo = data.get("tipo")
        
        if tipo == "tarea":
            guardar_tarea(usuario_id, data.get("tarea"), data.get("prioridad", "Media"), data.get("fecha_limite", "Pronto"))
            return f"📌 Tarea registrada con prioridad **{data.get('prioridad', 'Media')}**: *{data.get('tarea')}* (Fecha límite: {data.get('fecha_limite')})."
        
        elif tipo == "gasto":
            monto = float(data.get("monto", 0))
            cat = data.get("categoria", "General").strip().title()
            desc = data.get("descripcion", "Compra")
            alerta = registrar_transaccion(usuario_id, "gasto", monto, cat, desc)
            return f"💸 Gasto registrado: **-${monto:,.0f}** en *{cat}* ({desc}).{alerta}"
            
        elif tipo == "ingreso":
            monto = float(data.get("monto", 0))
            cat = data.get("categoria", "Ingreso").strip().title()
            desc = data.get("descripcion", "Pago recibido")
            registrar_transaccion(usuario_id, "ingreso", monto, cat, desc)
            return f"💰 ¡Ingreso registrado!: **+${monto:,.0f}** en *{cat}* ({desc}). Bien hecho, a capitalizar."
            
        elif tipo == "presupuesto":
            cat = data.get("categoria", "General").strip().title()
            limite = float(data.get("limite", 0))
            establecer_presupuesto(usuario_id, cat, limite)
            return f"🎯 Presupuesto fijado: Máximo **${limite:,.0f}** para la categoría *{cat}*."
            
    except Exception as e:
        print(f"Error procesando intención natural: {e}")
        pass
        
    return None

def pensar_respuesta(prompt_usuario: str) -> str:
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=f"{SYSTEM_INSTRUCTION}\n\nMensaje del usuario: {prompt_usuario}",
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                ]
            )
        )
        return response.text or ""
    except Exception as e:
        return f"Error en sistemas: {e}"

def pensar_respuesta_audio(ruta_audio: str, prompt_adicional: str = "") -> str:
    try:
        audio_file = client.files.upload(file=ruta_audio)
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[SYSTEM_INSTRUCTION, audio_file],
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                ]
            )
        )
        try: client.files.delete(name=audio_file.name)
        except: pass
        return response.text or ""
    except Exception as e:
        return f"Error al procesar audio: {e}"