"""Deterministic parsers. No Firestore writes here."""
import re
from datetime import datetime, timedelta

from modules.nlp.amounts import _normalizar_monto

def _parse_tarea(texto: str) -> dict | None:
    """Extrae tarea, prioridad y fecha de un mensaje de tarea."""
    texto_lower = texto.lower()

    # Detectar prioridad
    prioridad = "Media"
    if any(w in texto_lower for w in ["urgente", "crítica", "crítico"]):
        prioridad = "Alta"
    elif any(w in texto_lower for w in ["baja", "cuando pueda"]):
        prioridad = "Baja"

    # Detectar fecha límite
    fecha = "Pronto"
    if any(w in texto_lower for w in ["mañana", "manana"]):
        fecha = "Mañana"
    elif "hoy" in texto_lower:
        fecha = "Hoy"
    elif "semana" in texto_lower:
        fecha = "Esta semana"

    # Extraer descripción de la tarea
    patrones = [
        r'(?:agrega?|crea?|nueva?)?\s*tarea\s+(.+?)(?:\s+(?:prioridad|prioridad|alt[ao]|baja|urgente|mañana|manana|manana|hoy|esta semana))?$',
        r'(?:agrega?|crea?)?\s*(.+?)\s+(?:como\s+)?(?:tarea|pendiente|recordar)',
        r'(?:recordar|recuerdame|recordame)\s+(.+?)$',
    ]
    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            tarea = match.group(1).strip()
            if len(tarea) > 2:
                return {"tarea": tarea.title(), "prioridad": prioridad, "fecha_limite": fecha}

    # Si no matcheó ningún patrón pero dice "tarea"
    if "tarea" in texto_lower:
        # Tomar todo después de "tarea" o "nueva tarea"
        tarea = re.sub(r'^.*?tarea\s+', '', texto_lower).strip()
        tarea = re.sub(r'\s*(prioridad|alt[ao]|baja|urgente|mañana|manana|manana|hoy|esta semana).*$', '', tarea).strip()
        if len(tarea) > 2:
            return {"tarea": tarea.title(), "prioridad": prioridad, "fecha_limite": fecha}

    return None

def _parse_completar_tarea(texto: str) -> str | None:
    """Extrae el nombre de la tarea a completar."""
    texto_lower = texto.lower()

    patrones = [
        r'complet[oéé]\s+(.+)',
        r'hecho\s+(.+)',
        r'termin[oé]\s+(.+)',
        r'borrar\s+(.+)',
        r'eliminar\s+(.+)',
        r'done\s+(.+)',
    ]
    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            tarea = match.group(1).strip()
            if len(tarea) > 1:
                return tarea

    return None

