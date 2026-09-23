"""modules/memory/rag.py - Memoria episódica con ChromaDB (RAG ligero).

Almacena los resúmenes diarios/semanales que generan los cron jobs y permite
consultarlos por similitud semántica. Es de SOLO LECTURA respecto a Firestore:
nunca crea ni modifica datos financieros.

ChromaDB persiste en disco local (`data/chroma_db`). En Render el filesystem es
efímero, así que la memoria se reinicia con cada deploy salvo que se monte un
disco persistente en esa ruta. Todas las funciones degradan a no-op si
ChromaDB no está instalado o falla, para no tumbar el bot.
"""
import hashlib
import os

try:
    import chromadb
except ImportError:  # Permite arrancar el bot sin la dependencia instalada.
    chromadb = None

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma_db")

_collection = None


def _get_collection():
    """Devuelve la colección persistente, o None si ChromaDB no está disponible."""
    global _collection
    if _collection is not None:
        return _collection
    if chromadb is None:
        return None
    try:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        cliente = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = cliente.get_or_create_collection(
            name="jarvis_memory",
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:
        print(f"Memoria episódica no disponible: {e}")
        return None
    return _collection


def almacenar_resumen(documento: str, metadata: dict) -> bool:
    """Vectoriza y guarda un resumen o evento. Devuelve False si no pudo.

    Args:
        documento: Texto del resumen o evento.
        metadata: Metadatos (fecha, tipo, usuario_id, etc.). Deben ser escalares.
    """
    coleccion = _get_collection()
    if coleccion is None or not documento:
        return False

    base = f"{metadata.get('fecha', '')}_{metadata.get('tipo', '')}_{documento[:50]}"
    doc_id = hashlib.md5(base.encode()).hexdigest()
    try:
        coleccion.upsert(documents=[documento], metadatas=[metadata], ids=[doc_id])
        return True
    except Exception as e:
        print(f"Error guardando en memoria episódica: {e}")
        return False


def consultar_memoria(query: str, n_results: int = 3) -> list[dict]:
    """Consulta semántica a la memoria episódica.

    Returns:
        Lista de diccionarios con 'documento', 'metadata' y 'distancia'.
    """
    coleccion = _get_collection()
    if coleccion is None or not query:
        return []

    try:
        results = coleccion.query(query_texts=[query], n_results=n_results)
    except Exception as e:
        print(f"Error consultando memoria episódica: {e}")
        return []

    documentos = (results.get("documents") or [[]])[0]
    if not documentos:
        return []

    metadatos = (results.get("metadatas") or [[]])[0]
    distancias = (results.get("distances") or [[]])[0]

    return [
        {
            "documento": doc,
            "metadata": metadatos[i] if i < len(metadatos) else {},
            "distancia": distancias[i] if i < len(distancias) else None,
        }
        for i, doc in enumerate(documentos)
    ]


def obtener_contexto_historico(query: str) -> str:
    """Contexto histórico formateado para inyectar en el prompt de Gemini."""
    resultados = consultar_memoria(query, n_results=5)
    if not resultados:
        return ""

    lineas = ["CONTEXTO HISTÓRICO (memoria episódica de resúmenes pasados):"]
    for r in resultados:
        fecha = r["metadata"].get("fecha", "fecha desconocida")
        tipo = r["metadata"].get("tipo", "evento")
        lineas.append(f"- [{fecha}] {tipo}: {r['documento']}")
    return "\n".join(lineas)
