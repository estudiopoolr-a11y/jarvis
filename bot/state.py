"""
bot/state.py - Estado en memoria compartido del bot Discord.

Contiene caches, cooldowns y seguimiento de conversaciones activas.
Se importa en handlers y services que necesiten estado global.
"""
import time
from datetime import datetime, timedelta

# ============================================================
# CONFIGURACIÓN DE TIEMPOS
# ============================================================
_CONVERSACION_TTL = 180          # 3 minutos sin mencionar
_CONVERSACION_MAX_MENSAJES = 10  # máx mensajes sin @Jarvis
_CACHE_TTL = 30                  # segundos cache finanzas
_COOLDOWN_SEGUNDOS = 3           # anti-spam

# ============================================================
# ESTADOS GLOBALES (in-memory, se pierden al reiniciar)
# ============================================================

# Usuarios silenciados: {usuario_id: datetime_expiracion}
usuarios_silenciados: dict[str, datetime] = {}

# Usuarios con modo voz activado: set(usuario_id)
usuarios_modo_voz: set[str] = set()

# Canales donde ha habido actividad reciente: set(canal_id)
canales_activos: set[int] = set()

# Conversaciones activas por usuario:
# {usuario_id: {"timestamp": float, "canal_id": int, "contador": int}}
conversaciones_activas: dict[str, dict] = {}
consultas_presupuesto_activas: dict[str, float] = {}

# Cache de contexto financiero: {usuario_id: (datos_tuple, timestamp)}
_finanzas_cache: dict[str, tuple] = {}

# Cache de archivos TTS generados: {hash_texto: bool}
_tts_cache: dict[str, bool] = {}

# Cooldown anti-spam: {usuario_id: ultimo_timestamp}
_last_msg_time: dict[str, float] = {}


# ============================================================
# HELPERS DE ESTADO
# ============================================================

def limpiar_conversaciones_expiradas(ahora: float | None = None) -> None:
    """Elimina conversaciones cuyo TTL expiró."""
    if ahora is None:
        ahora = time.time()
    expirados = [
        uid for uid, data in conversaciones_activas.items()
        if isinstance(data, dict) and ahora - data.get("timestamp", 0) >= _CONVERSACION_TTL
    ]
    for uid in expirados:
        del conversaciones_activas[uid]


def hay_conversacion_activa(usuario_id: str, canal_id: int, ahora: float | None = None) -> bool:
    """Verifica si el usuario tiene una conversación activa en este canal."""
    if ahora is None:
        ahora = time.time()
    data = conversaciones_activas.get(usuario_id)
    if not data or not isinstance(data, dict):
        return False
    return (
        data.get("canal_id") == canal_id
        and ahora - data.get("timestamp", 0) < _CONVERSACION_TTL
        and data.get("contador", 0) < _CONVERSACION_MAX_MENSAJES
    )


def registrar_mensaje_conversacion(usuario_id: str, canal_id: int) -> None:
    """Actualiza o crea entrada de conversación activa."""
    ahora = time.time()
    if usuario_id in conversaciones_activas and isinstance(conversaciones_activas[usuario_id], dict):
        conversaciones_activas[usuario_id]["timestamp"] = ahora
        conversaciones_activas[usuario_id]["contador"] += 1
    else:
        conversaciones_activas[usuario_id] = {
            "timestamp": ahora,
            "canal_id": canal_id,
            "contador": 1,
        }


def completar_consulta_presupuesto(usuario_id: str, texto: str, ahora: float | None = None) -> str:
    """Completa un seguimiento de mes sin enviarlo como frase suelta a Gemini."""
    momento = time.time() if ahora is None else ahora
    texto_lc = texto.lower().strip()
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "setiembre", "octubre", "noviembre", "diciembre")
    if "presupuesto" in texto_lc and any(p in texto_lc for p in ("dame", "ver", "mostrar", "lista")):
        consultas_presupuesto_activas[usuario_id] = momento
        return texto
    if (texto_lc.startswith("de ") or texto_lc in meses) and any(m in texto_lc for m in meses):
        ultima = consultas_presupuesto_activas.get(usuario_id)
        if ultima is not None and momento - ultima < _CONVERSACION_TTL:
            consultas_presupuesto_activas[usuario_id] = momento
            return f"dame los presupuestos {texto_lc}"
    return texto


def verificar_cooldown(usuario_id: str) -> bool:
    """Retorna True si el usuario está en cooldown (no debe procesarse)."""
    ahora = time.time()
    if _last_msg_time.get(usuario_id, 0) >= ahora - _COOLDOWN_SEGUNDOS:
        return True
    _last_msg_time[usuario_id] = ahora
    return False


def obtener_contexto_cacheado(usuario_id: str, obtener_fn) -> tuple:
    """
    Devuelve datos cacheados o llama a obtener_fn() si expiró.

    obtener_fn: callable() -> (balance, ingresos, gastos, movimientos, presupuestos)
    """
    ahora = time.time()
    if usuario_id in _finanzas_cache:
        datos, timestamp = _finanzas_cache[usuario_id]
        if ahora - timestamp < _CACHE_TTL:
            return datos
    datos = obtener_fn()
    _finanzas_cache[usuario_id] = (datos, ahora)
    return datos


def cache_tts_hit(texto: str, output_path: str) -> bool:
    """Verifica si ya existe archivo TTS para este texto."""
    import hashlib
    cache_key = hashlib.md5(texto.encode("utf-8")).hexdigest()
    return cache_key in _tts_cache and os.path.exists(output_path)


def cache_tts_store(texto: str) -> None:
    """Marca texto como generado en cache TTS."""
    import hashlib
    cache_key = hashlib.md5(texto.encode("utf-8")).hexdigest()
    _tts_cache[cache_key] = True


# Import os aquí para evitar dependencia circular al importar state en tts
import os
