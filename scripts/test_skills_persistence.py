#!/usr/bin/env python3
"""Script para probar la lectura y persistencia de skills en Hermes Agent con normalización de texto."""

import sys
import os
import asyncio

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.firestore.client import inicializar_firebase, get_db, _get_user_ref
from src.agent.hermes_engine import _cargar_skills
from src.agent.tools import _normalizar_texto

async def test_skills_normalizacion():
    print("Inicializando Firebase...")
    inicializar_firebase()
    
    db = get_db()
    if not db:
        print("ERROR: No se pudo inicializar Firebase")
        return False
        
    print("Firebase inicializado correctamente")
    
    # Obtener referencia de usuario
    database, user_ref = _get_user_ref('default')
    if not user_ref:
        print("ERROR: No se pudo obtener referencia de usuario")
        return False
        
    print("Referencia de usuario obtenida")
    
    # Limpiar skills de prueba anteriores para evitar conflictos
    print("\nLimpiando skills de prueba anteriores...")
    skills_ref = user_ref.collection('skills')
    skills_existentes = skills_ref.stream()
    for skill_doc in skills_existentes:
        skill_data = skill_doc.to_dict()
        if skill_data:
            nombre = skill_data.get('nombre', '')
            nombre_normalizado = _normalizar_texto(nombre)
            if nombre_normalizado in ['ejemplo_inicial', 'ejemplo_inicial_2']:
                print(f"Eliminando skill de prueba: {nombre}")
                skill_doc.reference.delete()
    
    # Probar la función _cargar_skills de Hermes Agent
    print("\nProbando _cargar_skills de Hermes Agent...")
    skills_context = await _cargar_skills('default')
    if skills_context:
        print("Skills cargadas exitosamente:")
        print(skills_context)
    else:
        print("No se encontraron skills (esto es esperado si solo tenemos la skill de ejemplo)")
    
    # Añadir una nueva skill para probar persistencia y normalización
    print("\nAñadiendo nueva skill de prueba con variaciones de mayúsculas/minúsculas...")
    
    # Importar la herramienta de guardado para probar la normalización en la escritura
    from src.agent.tools import _guardar_skill
    
    # Probar con diferentes variaciones del mismo nombre
    variaciones = [
        'ejemplo_inicial',
        'EJEMPLO_INICIAL',
        'Ejemplo_Inicial',
        '  ejemplo_inicial  ',
        'ejemplo_inicial_2',
        'EJEMPLO_INICIAL_2'
    ]
    
    for i, variacion in enumerate(variaciones):
        # Usamos la función _guardar_skill que ahora implementa la normalización
        resultado = _guardar_skill(
            usuario_id='default',
            nombre=variacion,
            contenido=f'Contenido de prueba {i+1} para {variacion}',
            tipo='regla'
        )
        # Usar ASCII para evitar problemas de codificación en Windows
        print(f"Resultado para '{variacion}': {resultado.encode('ascii', errors='replace').decode('ascii')}")
    
    # Volver a cargar skills para ver si se aplicó la normalización
    print("\nRecargando skills después de añadir variaciones...")
    skills_context_updated = await _cargar_skills('default')
    if skills_context_updated:
        print("Contexto de skills actualizado:")
        # Usar ASCII para evitar problemas de codificación
        print(skills_context_updated.encode('ascii', errors='replace').decode('ascii'))
        
        # Contar cuántas skills con nombre normalizado 'ejemplo_inicial' existen
        lineas = skills_context_updated.split('\n')
        contador_ejemplo = 0
        for linea in lineas:
            if 'ejemplo_inicial' in linea.lower() and '[' in linea and ']' in linea:
                contador_ejemplo += 1
                
        print(f"\nNumero de skills con variaciones de 'ejemplo_inicial': {contador_ejemplo}")
        
        # Con normalización aplicada en la escritura, debería haber solo 1 skill (la última sobrescribe a las anteriores)
        if contador_ejemplo <= 1:
            print("[SUCCESS] La normalización está funcionando correctamente en la escritura")
            print("   Las habilidades con nombres que normalizan al mismo valor están siendo manejadas correctamente (evitando duplicados)")
        else:
            print("[WARNING] Aún hay múltiples skills con el mismo nombre normalizado")
            print("   Esto podría indicar que la normalización no se está aplicando completamente en la escritura")
    else:
        print("ERROR: No se pudieron cargar las skills después de persistirlas")
        return False
    
    # Probar específicamente la función de normalización
    print("\nProbando función _normalizar_texto directamente...")
    pruebas_normalizacion = [
        ('ejemplo_inicial', 'ejemplo_inicial'),
        ('EJEMPLO_INICIAL', 'ejemplo_inicial'),
        ('Ejemplo_Inicial', 'ejemplo_inicial'),
        ('  ejemplo_inicial  ', 'ejemplo_inicial'),
        ('ejemplo_inicial_2', 'ejemplo_inicial_2'),
        ('EJEMPLO_INICIAL_2', 'ejemplo_inicial_2'),
        ('habilidad con tildes', 'habilidad con tildes'),
        ('Habilidad Con Tildes', 'habilidad con tildes'),
        ('  habilidad con tildes  ', 'habilidad con tildes')
    ]
    
    todas_correctas = True
    for entrada, esperado in pruebas_normalizacion:
        resultado = _normalizar_texto(entrada)
        if resultado == esperado:
            print(f"[OK] '{entrada}' -> '{resultado}'")
        else:
            print(f"[ERROR] '{entrada}' -> '{resultado}' (esperado: '{esperado}')")
            todas_correctas = False
    
    if todas_correctas:
        print("[SUCCESS] Todas las pruebas de normalización pasaron correctamente")
    else:
        print("[FAILURE] Algunas pruebas de normalización fallaron")
        return False
    
    return True

def main():
    try:
        result = asyncio.run(test_skills_normalizacion())
        return result
    except Exception as e:
        print(f"ERROR durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)