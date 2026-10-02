#!/usr/bin/env python3
"""Script para verificar y inicializar la colección de skills en Firestore."""

import sys
import os

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.firestore.client import inicializar_firebase, get_db, _get_user_ref

def main():
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
    
    # Verificar colección skills
    skills_ref = user_ref.collection('skills')
    docs = list(skills_ref.limit(1).stream())
    
    if docs:
        print(f"Colección skills ya existe con {len(docs)}+ documentos")
        for doc in docs:
            print(f"  - {doc.id}: {doc.to_dict()}")
    else:
        print("Colección skills existe pero está vacía - creando skill de ejemplo...")
        # Crear una skill de ejemplo
        example_skill = {
            'tipo': 'preferencia',
            'nombre': 'ejemplo_inicial',
            'contenido': 'Esta es una skill de ejemplo para inicializar la colección'
        }
        doc_ref = skills_ref.add(example_skill)
        print(f"Skill de ejemplo creada exitosamente con ID: {doc_ref[1].id}")
    
    # Verificar que podemos leer skills
    print("\nVerificando lectura de skills...")
    all_skills = list(skills_ref.stream())
    print(f"Total de skills encontradas: {len(all_skills)}")
    for skill in all_skills[:3]:  # Mostrar solo las primeras 3
        print(f"  - {skill.id}: {skill.to_dict()}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)