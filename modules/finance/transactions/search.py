"""Submódulo para búsqueda y sugerencias de transacciones."""

from datetime import datetime, timedelta
from firebase_admin import firestore
from modules.firestore.client import _get_user_ref
from modules.firestore.users import ensure_user
from modules.finance.accounts import listar_cuentas
from modules.finance.categories import listar_categorias


def buscar_transacciones(usuario_id, texto="", categoria="", cuenta="", status="",
                       fecha_desde="", fecha_hasta="", tipo="", tags=None,
                       limite=100):
    """Búsqueda avanzada de transacciones con múltiples filtros."""
    if tags is None:
        tags = []
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        # Obtener categorías y cuentas para mapear IDs
        cats = listar_categorias(usuario_id)
        cat_nombres = {c["_id"]: c.get("nombre", "") for c in cats}
        cuentas = listar_cuentas(usuario_id)
        cuenta_nombres = {c["_id"]: c.get("nombre", "") for c in cuentas}

        resultados = []
        ahora = datetime.now()

        # Buscar en últimos 12 meses
        for i in range(12):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            try:
                docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
                for d in docs:
                    t = d.to_dict()
                    t["_id"] = d.id
                    t["_year"] = year
                    t["_month"] = month

                    # Filtro por texto
                    if texto:
                        desc = (t.get("description") or "").lower()
                        payee = (t.get("payee") or "").lower()
                        if texto.lower() not in desc and texto.lower() not in payee:
                            continue

                    # Filtro por categoría
                    if categoria:
                        cat_id = t.get("category_id", "")
                        cat_nombre = cat_nombres.get(cat_id, "")
                        if categoria.lower() not in cat_nombre.lower():
                            continue

                    # Filtro por cuenta
                    if cuenta:
                        acc_id = t.get("account_id", "")
                        acc_nombre = cuenta_nombres.get(acc_id, "")
                        if cuenta.lower() not in acc_nombre.lower():
                            continue

                    # Filtro por status
                    if status and t.get("status", "cleared") != status:
                        continue

                    # Filtro por tipo
                    tipo_val = t.get("type") or t.get("tipo", "expense")
                    if tipo and tipo_val != tipo:
                        continue

                    # Filtro por rango de fechas
                    fecha_tx = t.get("date") or t.get("fecha", "")
                    if fecha_desde and fecha_tx < fecha_desde:
                        continue
                    if fecha_hasta and fecha_tx > fecha_hasta:
                        continue

                    # Filtro por tags
                    if tags:
                        t_tags = t.get("tags", [])
                        if not any(tag in t_tags for tag in tags):
                            continue

                    resultados.append(t)
            except Exception:
                pass

        # Ordenar por fecha descendente
        resultados.sort(key=lambda x: x.get("date") or x.get("fecha", ""), reverse=True)
        return resultados[:limite]
    except Exception as e:
        print(f"Error en búsqueda avanzada: {e}")
        return []


def obtener_sugerencias_payee(usuario_id, prefijo, limite=10):
    """Obtiene sugerencias de payee basadas en el historial."""
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        # Contar frecuencia de cada payee
        ahora = datetime.now()
        conteo = {}

        for i in range(12):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            try:
                docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
                for d in docs:
                    t = d.to_dict()
                    payee = t.get("payee", "")
                    if payee and prefijo.lower() in payee.lower():
                        conteo[payee] = conteo.get(payee, 0) + 1
            except Exception:
                pass

        # Ordenar por frecuencia
        sugeridos = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
        return [{"payee": p, "frecuencia": f} for p, f in sugeridos[:limite]]
    except Exception:
        return []


def obtener_sugerencias_categoria(usuario_id, prefijo, limite=10):
    """Sugiere categorías por comercio conocido y, después, por historial."""
    _CATEGORIAS_POR_COMERCIO = {
        "d1": "Alimentación",
        "exito": "Alimentación",
        "éxito": "Alimentación",
        "carulla": "Alimentación",
        "oxxo": "Alimentación",
        "jumbo": "Alimentación",
        "ara": "Alimentación",
        "rappi": "Alimentación",
        "uber": "Transporte",
        "didi": "Transporte",
        "cabify": "Transporte",
        "terpel": "Transporte",
        "primax": "Transporte",
        "netflix": "Entretenimiento",
        "spotify": "Entretenimiento",
        "claro": "Celular",
        "movistar": "Celular",
        "tigo": "Celular",
        "eps": "Salud",
        "farmatodo": "Salud",
        "cruz verde": "Salud",
    }

    comercio = (prefijo or "").casefold().strip()
    conocidas = [
        {"categoria": categoria, "frecuencia": 0, "origen": "comercio"}
        for nombre, categoria in _CATEGORIAS_POR_COMERCIO.items()
        if nombre in comercio or comercio in nombre
    ]
    if conocidas:
        return conocidas[:limite]
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return []
    try:
        conteo = {}
        ahora = datetime.now()

        for i in range(12):
            mes_date = ahora - timedelta(days=30 * i)
            year = str(mes_date.year)
            month = f"{mes_date.month:02d}"
            try:
                docs = user_ref.collection("transactions").document(f"{year}-{month}").collection("items").stream()
                for d in docs:
                    t = d.to_dict()
                    cat_id = t.get("category_id", "")
                    if not cat_id:
                        continue
                    # Obtener nombre de categoría
                    cats = listar_categorias(usuario_id)
                    cat_nombre = next((c.get("nombre", "") for c in cats if c.get("_id") == cat_id), "")
                    if cat_nombre and prefijo.lower() in cat_nombre.lower():
                        conteo[cat_nombre] = conteo.get(cat_nombre, 0) + 1
            except Exception:
                pass

        sugeridos = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
        return [{"categoria": c, "frecuencia": f} for c, f in sugeridos[:limite]]
    except Exception:
        return []