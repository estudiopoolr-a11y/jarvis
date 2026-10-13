# modules/tasks/firebase_manager.py
# Gestor CRUD de tareas en Firebase Firestore.
# Colección: tasks/{user_id}/items/{task_id}

import firebase_admin  # Importar SDK Firebase Admin para acceso a servicios //
from firebase_admin import firestore  # Importar cliente de base de datos NoSQL //
from datetime import datetime  # Importar módulo datetime para marcas temporales //


def obtener_cliente_firestore():  # Inicializar y retornar cliente Firestore //
    """Retorna la instancia singleton de Firestore del proyecto."""
    db = firestore.client()  # Instanciar el cliente oficial de Firestore //
    return db  # Retornar instancia lista para consultas //


def agregar_tarea(usuario_id: str, titulo: str, descripcion: str = "") -> dict:  # Crear tarea en subcolección del usuario //
    """Agrega una nueva tarea a tasks/{user_id}/items con ID generado automáticamente."""
    db = obtener_cliente_firestore()  # Obtener instancia de Firestore //
    ref_items = db.collection("tasks").document(usuario_id).collection("items")  # Apuntar a subcolección items del usuario //

    nuevo_doc = ref_items.document()  # Generar ID único automático para el documento //
    datos_tarea = {  # Construir diccionario con campos de la tarea //
        "id": nuevo_doc.id,  # Asignar identificador único generado por Firestore //
        "titulo": titulo,  # Guardar título o descripción principal de la tarea //
        "descripcion": descripcion,  # Guardar detalles adicionales (opcional) //
        "completada": False,  # Estado inicial: pendiente //
        "fecha_creacion": datetime.now().isoformat(),  # Marca temporal de creación ISO 8601 //
        "usuario_id": str(usuario_id),  # Referencia al propietario de la tarea //
    }  # Fin del diccionario de datos //

    nuevo_doc.set(datos_tarea)  # Escribir documento de forma atómica en Firestore //
    return datos_tarea  # Retornar tarea creada con su ID asignado //


def listar_tareas_pendientes(usuario_id: str) -> list:  # Consultar tareas no completadas del usuario //
    """Lista todas las tareas pendientes (completada=False) de tasks/{user_id}/items."""
    db = obtener_cliente_firestore()  # Obtener instancia de Firestore //
    ref_items = db.collection("tasks").document(usuario_id).collection("items")  # Apuntar a subcolección items //

    docs = ref_items.where("completada", "==", False).stream()  # Filtrar solo tareas pendientes //

    lista_tareas = []  # Inicializar contenedor de resultados //
    for doc in docs:  # Iterar sobre documentos coincidentes //
        tarea = doc.to_dict()  # Convertir documento a diccionario Python //
        tarea["id"] = doc.id  # Inyectar el ID del documento para referencia posterior //
        lista_tareas.append(tarea)  # Agregar tarea a la lista //

    return lista_tareas  # Retornar lista de tareas pendientes //


def listar_todas_tareas(usuario_id: str) -> list:  # Consultar todas las tareas del usuario //
    """Lista todas las tareas (completadas y pendientes) de tasks/{user_id}/items."""
    db = obtener_cliente_firestore()  # Obtener instancia de Firestore //
    ref_items = db.collection("tasks").document(usuario_id).collection("items")  # Apuntar a subcolección items //

    docs = ref_items.stream()  # Leer todos los documentos sin filtrar //

    lista_tareas = []  # Inicializar contenedor //
    for doc in docs:  # Iterar sobre cada documento //
        tarea = doc.to_dict()  # Convertir documento a diccionario //
        tarea["id"] = doc.id  # Inyectar ID del documento //
        lista_tareas.append(tarea)  # Agregar a la lista //

    return lista_tareas  # Retornar todas las tareas del usuario //


def marcar_tarea_completada(usuario_id: str, tarea_id: str) -> bool:  # Marcar tarea específica como completada //
    """Marca una tarea como completada (completada=True) por su ID de documento."""
    db = obtener_cliente_firestore()  # Obtener instancia de Firestore //
    ref_tarea = db.collection("tasks").document(usuario_id).collection("items").document(tarea_id)  # Referencia directa al documento //

    try:  # Intentar actualizar el documento //
        ref_tarea.update({"completada": True})  # Actualizar campo completada a True //
        return True  # Retornar éxito //
    except Exception as e:  # Capturar errores (documento no encontrado, etc.) //
        print(f"[tasks] Error marcando tarea completada: {e}")  # Log del error //
        return False  # Retornar fracaso //


def eliminar_tarea(usuario_id: str, tarea_id: str) -> bool:  # Eliminar tarea por ID //
    """Elimina una tarea de tasks/{user_id}/items por su ID de documento."""
    db = obtener_cliente_firestore()  # Obtener instancia de Firestore //
    ref_tarea = db.collection("tasks").document(usuario_id).collection("items").document(tarea_id)  # Referencia al documento //

    try:  # Intentar eliminar el documento //
        ref_tarea.delete()  # Borrar documento de Firestore //
        return True  # Retornar éxito //
    except Exception as e:  # Capturar errores //
        print(f"[tasks] Error eliminando tarea: {e}")  # Log del error //
        return False  # Retornar fracaso //
