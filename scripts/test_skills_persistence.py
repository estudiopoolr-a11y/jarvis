#!/usr/bin/env python3
"""Script para probar la lectura y persistencia de skills en Hermes Agent."""

import sys
import os
import asyncio

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.firestore.client import inicializar_firebase, get_db, _get_user_ref
from src.agent.hermes_engine import _cargar_skills

async def test_skills_operations():
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
    
    # Probar la función _cargar_skills de Hermes Agent
    print("\nProbando _cargar_skills de Hermes Agent...")
    skills_context = await _cargar_skills('default')
    if skills_context:
        print("Skills cargadas exitosamente:")
        print(skills_context)
    else:
        print("No se encontraron skills (esto es esperado si solo tenemos la skill de ejemplo)")
    
    # Añadir una nueva skill para probar persistencia
    print("\nAñadiendo nueva skill de prueba...")
    skills_ref = user_ref.collection('skills')
    new_skill = {
        'tipo': 'regla',
        'nombre': 'regla_prueba_persistencia',
        'contenido': 'Esta es una regla de prueba para verificar persistencia'
    }
    doc_ref = skills_ref.add(new_skill)
    print(f"Nueva skill creada con ID: {doc_ref[1].id}")
    
    # Volver a cargar skills para ver la nueva
    print("\nRecargando skills después de añadir nueva...")
    skills_context_updated = await _cargar_skills('default')
    if skills_context_updated and 'regla_prueba_persistencia' in skills_context_updated:
        print("¡Éxito! La nueva skill se leyó correctamente después de persistirla")
        print("Contexto de skills actualizado:")
        print(skills_context_updated)
    else:
        print("ERROR: No se pudo leer la nueva skill después de persistirla")
        return False
    
    return True

def main():
    try:
        result = asyncio.run(test_skills_operations())
        return result
    except Exception as e:
        print(f"ERROR durante la ejecución: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)