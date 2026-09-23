"""app/routes/memory.py - Endpoints REST para Memoria Episódica (RAG Ligero).

Permite ingerir resúmenes y consultar la memoria vectorial desde otros servicios
o herramientas externas. Todas las operaciones son de SOLO LECTURA respecto a
Firestore: nunca crean ni modifican datos financieros.
"""
from fastapi import APIRouter, HTTPException

from modules.memory.rag import almacenar_resumen, consultar_memoria, obtener_contexto_historico

router = APIRouter(prefix="/api/memory", tags=["memoria"])


@router.post("/store")
def store_summary(
    documento: str,
    metadata: dict,
):
    """Almacena un resumen o evento en la memoria episódica.

    Args:
        documento: Texto del resumen o evento.
        metadata: Metadatos (fecha, tipo, usuario_id, etc.).
    """
    if not documento or not metadata:
        raise HTTPException(status_code=400, detail="documento y metadata son requeridos")

    # Validar campos mínimos
    if "fecha" not in metadata or "tipo" not in metadata:
        raise HTTPException(status_code=400, detail="metadata debe incluir 'fecha' y 'tipo'")

    exito = almacenar_resumen(documento, metadata)
    if not exito:
        raise HTTPException(status_code=500, detail="Error al almacenar en memoria episódica")

    return {"status": "ok", "mensaje": "Resumen almacenado correctamente"}


@router.get("/query")
def query_memory(query: str, n_results: int = 3):
    """Consulta semántica a la memoria episódica.

    Args:
        query: Texto de búsqueda.
        n_results: Número de resultados a retornar.
    """
    if not query:
        raise HTTPException(status_code=400, detail="query es requerido")

    resultados = consultar_memoria(query, n_results=n_results)
    return {"resultados": resultados}


@router.get("/context")
def get_historical_context(query: str):
    """Contexto histórico formateado para inyectar en el prompt de Gemini."""
    if not query:
        raise HTTPException(status_code=400, detail="query es requerido")

    contexto = obtener_contexto_historico(query)
    return {"contexto": contexto}
