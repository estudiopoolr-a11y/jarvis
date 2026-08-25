import sys
import os
from google import genai
# Importamos las nuevas funciones de memoria optimizada
from database import guardar_mensaje, obtener_contexto_optimizado, actualizar_resumen

API_KEY = os.getenv("GEMINI_API_KEY")
CHAT_ID = "usuario_test" 

client = genai.Client(api_key=API_KEY)

mensaje_usuario = input("Tú: ")

# 1. Obtenemos el contexto optimizado (Resumen + últimos 3 mensajes)
contexto = obtener_contexto_optimizado(CHAT_ID)

# 2. Preparamos un prompt que le da instrucciones a JARVIS
prompt_completo = f"""
{contexto}

Eres JARVIS, un asistente personal.
Instrucciones:
1. Responde al usuario de forma natural.
2. Si el usuario te da información sobre sus gustos, datos personales o planes, 
   añade al final de tu respuesta: [RESUMEN: lo que aprendiste brevemente].

Usuario dice: {mensaje_usuario}
"""

# 3. Llamamos a Gemini
interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt_completo
)

respuesta_jarvis = interaction.output_text

# 4. Lógica para procesar el resumen automáticamente
if "[RESUMEN:" in respuesta_jarvis:
    # Extraemos el texto que está dentro de los corchetes
    inicio = respuesta_jarvis.find("[RESUMEN:") + len("[RESUMEN:")
    fin = respuesta_jarvis.find("]", inicio)
    nuevo_dato = respuesta_jarvis[inicio:fin].strip()
    
    # Guardamos este nuevo dato en la memoria a largo plazo (Firebase)
    actualizar_resumen(CHAT_ID, nuevo_dato)
    
    # Limpiamos la respuesta para que al usuario no le aparezca el código raro
    respuesta_jarvis = respuesta_jarvis[:respuesta_jarvis.find("[RESUMEN:")]

# 5. Guardamos en el historial de mensajes (la memoria de corto plazo)
guardar_mensaje(CHAT_ID, "Usuario", mensaje_usuario)
guardar_mensaje(CHAT_ID, "JARVIS", respuesta_jarvis)

print(f"JARVIS: {respuesta_jarvis}")