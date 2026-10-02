#!/usr/bin/env python3
"""
Script para inspeccionar y limpiar duplicados en la colección raíz accounts de Firestore.
Lista todos los documentos, detecta duplicados por nombre (normalizado) y conserva solo el canónico.
"""

import sys
import os

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.firestore.client import get_db

def normalizar_nombre(nombre):
    """Normaliza el nombre a minúsculas y elimina espacios extra."""
    if not nombre:
        return ""
    return nombre.strip().lower()

def main():
    print("[INFO] Iniciando inspeccion de la coleccion 'accounts' en Firestore...")
    
    # Inicializar Firebase
    db = get_db()
    if not db:
        print("❌ Error: No se pudo inicializar Firebase")
        return 1
    
    print("[OK] Firebase inicializado correctamente")
    
    # Obtener todas las cuentas
    try:
        docs = db.collection("accounts").stream()
        cuentas = []
        for doc in docs:
            data = doc.to_dict()
            cuentas.append({
                'id': doc.id,
                'nombre': data.get('nombre', data.get('name', '')),
                'tipo': data.get('tipo', data.get('type', '')),
                'balance': data.get('balance', 0),
                'data_completa': data
            })
        
        print(f"\n[INFO] Encontradas {len(cuentas)} cuentas en la coleccion 'accounts':")
        print("-" * 80)
        for cuenta in cuentas:
            print(f"ID: {cuenta['id']:<20} | Nombre: {cuenta['nombre']:<15} | Tipo: {cuenta['tipo']:<10} | Balance: {cuenta['balance']}")
        
        if not cuentas:
            print("[WARN] No se encontraron cuentas en la coleccion")
            return 0
            
    except Exception as e:
        print(f"[ERROR] Error al leer la coleccion accounts: {e}")
        return 1
    
    # Detectar duplicados por nombre normalizado
    print("\n[INFO] Detectando duplicados por nombre (normalizado)...")
    nombres_vistos = {}
    duplicados = []
    
    for cuenta in cuentas:
        nombre_normalizado = normalizar_nombre(cuenta['nombre'])
        if nombre_normalizado in nombres_vistos:
            duplicados.append((cuenta, nombres_vistos[nombre_normalizado]))
        else:
            nombres_vistos[nombre_normalizado] = cuenta
    
    if not duplicados:
        print("[INFO] No se encontraron duplicados")
        return 0
    
    print(f"\n[WARN] Se encontraron {len(duplicados)} pares de duplicados:")
    print("-" * 80)
    for i, (dup, original) in enumerate(duplicados, 1):
        print(f"{i}. Duplicado: ID={dup['id']}, Nombre='{dup['nombre']}'")
        print(f"   Original: ID={original['id']}, Nombre='{original['nombre']}'")
    
    # Determinar qué cuentas mantener (canónicas: nu, nequi, efectivo)
    print("\n[INFO] Determinando cuentas canónicas a mantener...")
    cuentas_a_mantener = {}  # nombre_normalizado -> cuenta_a_mantener
    cuentas_a_eliminar = []  # lista de cuentas a eliminar
    
    # Primero, identificar las cuentas canónicas existentes
    nombres_canonicos = ['nu', 'nequi', 'efectivo']
    for cuenta in cuentas:
        nombre_norm = normalizar_nombre(cuenta['nombre'])
        if nombre_norm in nombres_canonicos:
            cuentas_a_mantener[nombre_norm] = cuenta
            print(f"[OK] Cuenta canónica encontrada: '{cuenta['nombre']}' (ID: {cuenta['id']})")
    
    # Para cada nombre, decidir qué mantener y qué eliminar
    for nombre_norm, cuentas_con_este_nombre in [(k, [v] + [d[0] for d in duplicados if normalizar_nombre(d[0]['nombre']) == k]) 
                                                 for k, v in nombres_vistos.items()]:
        # Si ya tenemos una cuenta canónica para este nombre, mantenerla
        if nombre_norm in cuentas_a_mantener:
            cuenta_mantener = cuentas_a_mantener[nombre_norm]
            # Todas las demás van a eliminar
            for cuenta in cuentas_con_este_nombre:
                if cuenta['id'] != cuenta_mantener['id']:
                    cuentas_a_eliminar.append(cuenta)
                    print(f"[DEL] Marcado para eliminar: '{cuenta['nombre']}' (ID: {cuenta['id']})")
        else:
            # No tenemos canónica, mantener la primera encontrada
            cuenta_mantener = cuentas_con_este_nombre[0]
            cuentas_a_mantener[nombre_norm] = cuenta_mantener
            print(f"[INFO] Manteniendo como canónica: '{cuenta_mantener['nombre']}' (ID: {cuenta_mantener['id']})")
            # Las demás van a eliminar
            for cuenta in cuentas_con_este_nombre[1:]:
                cuentas_a_eliminar.append(cuenta)
                print(f"[DEL] Marcado para eliminar: '{cuenta['nombre']}' (ID: {cuenta['id']})")
    
    # Eliminar duplicados
    if cuentas_a_eliminar:
        print(f"\n[INFO] Eliminando {len(cuentas_a_eliminar)} cuentas duplicadas...")
        eliminadas = 0
        fallidas = 0
        
        for cuenta in cuentas_a_eliminar:
            try:
                db.collection("accounts").document(cuenta['id']).delete()
                print(f"   [OK] Eliminada: '{cuenta['nombre']}' (ID: {cuenta['id']})")
                eliminadas += 1
            except Exception as e:
                print(f"   [ERROR] Error al eliminar '{cuenta['nombre']}' (ID: {cuenta['id']}): {e}")
                fallidas += 1
        
        print(f"\n[RESULT] Resultado: {eliminadas} eliminadas correctamente, {fallidas} fallidas")
    else:
        print("\n[INFO] No hay cuentas para eliminar")
    
    # Verificación final
    print("\n[INFO] Verificacion final de la coleccion...")
    try:
        docs = db.collection("accounts").stream()
        cuentas_finales = []
        for doc in docs:
            data = doc.to_dict()
            cuentas_finales.append({
                'id': doc.id,
                'nombre': data.get('nombre', data.get('name', '')),
                'tipo': data.get('tipo', data.get('type', '')),
                'balance': data.get('balance', 0)
            })
        
        print(f"[OK] Coleccion limpia: {len(cuentas_finales)} cuentas restantes:")
        print("-" * 80)
        for cuenta in cuentas_finales:
            print(f"ID: {cuenta['id']:<20} | Nombre: {cuenta['nombre']:<15} | Tipo: {cuenta['tipo']:<10} | Balance: {cuenta['balance']}")
            
    except Exception as e:
        print(f"[ERROR] Error en verificacion final: {e}")
        return 1
    
    print("\n[SUCCESS] Proceso de deduplicacion completado exitosamente")
    return 0

if __name__ == "__main__":
    sys.exit(main())