"""Firestore domain helpers. Do not import modules.db from here."""
from datetime import datetime, timedelta

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from modules.firestore.client import (
    USUARIO_PRINCIPAL,
    _get_user_ref,
    get_db,
    inicializar_firebase,
)

import re
import unicodedata
from modules.firestore.users import ensure_user

# ==================== CATEGORÍAS (KEBO) ====================

CATEGORIAS_PREDEFINIDAS = [
    {"nombre": "Alimentación", "icono": "🍔", "color": "#f59e0b", "tipo": "variable"},
    {"nombre": "Transporte", "icono": "🚗", "color": "#6366f1", "tipo": "variable"},
    {"nombre": "Servicios", "icono": "💡", "color": "#8b5cf6", "tipo": "fijo"},
    {"nombre": "Arriendo", "icono": "🏠", "color": "#ec4899", "tipo": "fijo"},
    {"nombre": "Entretenimiento", "icono": "🎬", "color": "#06b6d4", "tipo": "variable"},
    {"nombre": "Salud", "icono": "🏥", "color": "#ef4444", "tipo": "variable"},
    {"nombre": "Educación", "icono": "📚", "color": "#3b82f6", "tipo": "variable"},
    {"nombre": "Ropa", "icono": "👕", "color": "#10b981", "tipo": "variable"},
    {"nombre": "Hogar", "icono": "🏡", "color": "#84cc16", "tipo": "variable"},
    {"nombre": "Mascotas", "icono": "🐕", "color": "#f97316", "tipo": "variable"},
    {"nombre": "Celular", "icono": "📱", "color": "#a855f7", "tipo": "fijo"},
    {"nombre": "Internet", "icono": "🌐", "color": "#14b8a6", "tipo": "fijo"},
    {"nombre": "Deudas", "icono": "💳", "color": "#f43f5e", "tipo": "fijo"},
    {"nombre": "Ahorro", "icono": "🏦", "color": "#22c55e", "tipo": "variable"},
    {"nombre": "Inversión", "icono": "📈", "color": "#eab308", "tipo": "variable"},
    {"nombre": "Otros", "icono": "📦", "color": "#6b7280", "tipo": "variable"},
]

def listar_categorias(usuario_id="default"):
    """Lista todas las categorías."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        docs = user_ref.collection("categories").stream()
        return [{**d.to_dict(), "_id": d.id} for d in docs]
    except Exception as e:
        print(f"Error listando categorías: {e}")
        return []

def crear_categoria(usuario_id, nombre, budget=0, tipo="variable", icono="📊", color="#3b82f6"):
    """Crea una nueva categoría con presupuesto."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        ensure_user(usuario_id)
        existing = user_ref.collection("categories").where("nombre", "==", nombre).limit(1).stream()
        existing_list = list(existing)
        if existing_list:
            return existing_list[0].id
        doc_ref = user_ref.collection("categories").document()
        doc_ref.set({
            "nombre": nombre,
            "budget": float(budget),
            "tipo": tipo,
            "icono": icono,
            "color": color,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error creando categoría: {e}")
        return None

def crear_categorias_predefinidas(usuario_id="default"):
    """Crea todas las categorías predefinidas para un usuario."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0
    try:
        ensure_user(usuario_id)
        count = 0
        for cat in CATEGORIAS_PREDEFINIDAS:
            existing = user_ref.collection("categories").where("nombre", "==", cat["nombre"]).limit(1).stream()
            existing_list = list(existing)
            if not existing_list:
                doc_ref = user_ref.collection("categories").document()
                doc_ref.set({
                    "nombre": cat["nombre"],
                    "icono": cat["icono"],
                    "color": cat["color"],
                    "tipo": cat["tipo"],
                    "budget": 0.0,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                count += 1
        return count
    except Exception as e:
        print(f"Error creando categorías predefinidas: {e}")
        return 0


# ==================== SUB-CATEGORÍAS (KEBO) ====================

SUB_CATEGORIAS_PREDEFINIDAS = {
    "Alimentación": [
        {"nombre": "Restaurantes", "icono": "🍽️", "color": "#f59e0b"},
        {"nombre": "Mercado", "icono": "🛒", "color": "#10b981"},
        {"nombre": "Panadería", "icono": "🥖", "color": "#eab308"},
        {"nombre": "Café", "icono": "☕", "color": "#8b5cf6"},
        {"nombre": "Delivery", "icono": "🛵", "color": "#06b6d4"},
    ],
    "Transporte": [
        {"nombre": "Uber/DiDi", "icono": "🚗", "color": "#6366f1"},
        {"nombre": "Gasolina", "icono": "⛽", "color": "#ef4444"},
        {"nombre": "Transporte público", "icono": "🚌", "color": "#3b82f6"},
        {"nombre": "Parqueadero", "icono": "🅿️", "color": "#6b7280"},
    ],
    "Entretenimiento": [
        {"nombre": "Cine", "icono": "🎬", "color": "#ec4899"},
        {"nombre": "Streaming", "icono": "📺", "color": "#ef4444"},
        {"nombre": "Videojuegos", "icono": "🎮", "color": "#8b5cf6"},
        {"nombre": "Conciertos", "icono": "🎵", "color": "#f59e0b"},
    ],
    "Salud": [
        {"nombre": "Medicamentos", "icono": "💊", "color": "#ef4444"},
        {"nombre": "Doctor", "icono": "👨‍⚕️", "color": "#3b82f6"},
        {"nombre": "Gimnasio", "icono": "🏋️", "color": "#10b981"},
        {"nombre": "Veterinaria", "icono": "🐕", "color": "#f97316"},
    ],
}


def listar_subcategorias(usuario_id, categoria_nombre):
    """Lista sub-categorías de una categoría padre."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        # Buscar categoría padre
        cats = user_ref.collection("categories").where("nombre", "==", categoria_nombre).limit(1).stream()
        cats_list = list(cats)
        if not cats_list:
            return []
        cat_id = cats_list[0].id
        docs = user_ref.collection("categories").document(cat_id).collection("subcategories").stream()
        return [{**d.to_dict(), "_id": d.id} for d in docs]
    except Exception as e:
        print(f"Error listando subcategorías: {e}")
        return []


def crear_subcategoria(usuario_id, categoria_nombre, sub_nombre, icono="📁", color="#6b7280"):
    """Crea una sub-categoría dentro de una categoría padre."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return None
    try:
        cats = user_ref.collection("categories").where("nombre", "==", categoria_nombre).limit(1).stream()
        cats_list = list(cats)
        if not cats_list:
            return None
        cat_id = cats_list[0].id
        doc_ref = user_ref.collection("categories").document(cat_id).collection("subcategories").document()
        doc_ref.set({
            "nombre": sub_nombre,
            "icono": icono,
            "color": color,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error creando subcategoría: {e}")
        return None


def crear_subcategorias_predefinidas(usuario_id):
    """Crea todas las sub-categorías predefinidas para un usuario."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return 0
    count = 0
    for cat_nombre, subcats in SUB_CATEGORIAS_PREDEFINIDAS.items():
        cats = user_ref.collection("categories").where("nombre", "==", cat_nombre).limit(1).stream()
        cats_list = list(cats)
        if not cats_list:
            continue
        cat_id = cats_list[0].id
        for sub in subcats:
            existing = user_ref.collection("categories").document(cat_id).collection("subcategories").where("nombre", "==", sub["nombre"]).limit(1).stream()
            if not list(existing):
                user_ref.collection("categories").document(cat_id).collection("subcategories").document().set({
                    "nombre": sub["nombre"],
                    "icono": sub["icono"],
                    "color": sub["color"],
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                count += 1
    return count
def _normalizar_cat_str(s):
    """Normaliza un string de categoría para comparación insensible a acentos, puntuación y mayúsculas."""
    if not s:
        return ""
    s_norm = ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')
    s_clean = re.sub(r'[^\w\s]', '', s_norm).strip().casefold()
    return re.sub(r'\s+', ' ', s_clean)


def _cat_exacta(nombre_doc, busqueda):
    """Verifica si dos nombres de categoría coinciden exactamente tras normalizar."""
    d = _normalizar_cat_str(nombre_doc)
    b = _normalizar_cat_str(busqueda)
    return bool(d and b and d == b)


def _coincidir_categoria(nombre_doc, busqueda):
    """Compara nombres de categoría normalizando acentos, puntuación y mayúsculas."""
    d = _normalizar_cat_str(nombre_doc)
    b = _normalizar_cat_str(busqueda)
    if not d or not b:
        return False
    if d == b:
        return True
    if len(b) >= 3 and (b in d or d in b):
        return True
    return False

