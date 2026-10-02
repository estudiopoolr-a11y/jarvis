"""
src/agent/tools.py — Herramientas (Tools) de Firestore para el agente Hermes.

Cada herramienta sigue el contrato:
  - nombre (str): identificador único usado en function calling
  - descripcion (str): descripción que el LLM usa para decidir cuándo llamarla
  - parametros (dict): esquema JSON Schema de los parámetros
  - ejecutar(**kwargs) -> str: ejecuta la acción y devuelve texto legible

REGLAS AGENTS.md:
  - Mutaciones solo via flujo determinístico explícito.
  - Gemini opera en modo solo lectura; herramientas de escritura son llamadas
    desde el AgentTool, no directamente desde el LLM.
  - Nunca guardar tokens, contraseñas ni credenciales bancarias.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("JARVIS.tools")

# ---------------------------------------------------------------------------
# Contrato base de herramienta
# ---------------------------------------------------------------------------


class AgentTool:
    """Herramienta que el agente puede invocar."""

    def __init__(
        self,
        nombre: str,
        descripcion: str,
        parametros: Dict[str, Any],
        funcion: Callable[..., str],
    ):
        self.nombre = nombre
        self.descripcion = descripcion
        self.parametros = parametros
        self._funcion = funcion

    def ejecutar(self, **kwargs) -> str:
        """Ejecuta la herramienta y retorna texto legible."""
        try:
            return self._funcion(**kwargs)
        except Exception as exc:
            logger.error("Error en herramienta '%s': %s", self.nombre, exc, exc_info=True)
            raise

    def to_function_declaration(self) -> Dict[str, Any]:
        """Convierte la herramienta al formato function declaration del LLM."""
        return {
            "name": self.nombre,
            "description": self.descripcion,
            "parameters": self.parametros,
        }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _periodo_actual() -> str:
    """Retorna el periodo actual en formato YYYY-MM con dos dígitos."""
    return datetime.now().strftime("%Y-%m")


def _resolver_usuario_id(usuario_id: Optional[str]) -> str:
    """Rechaza IDs de prueba y usa el usuario real configurado."""
    if not usuario_id or usuario_id in ["usuario_1234", "user_1234", "default"]:
        usuario_id = os.getenv("DEFAULT_USER_ID") or os.getenv("USUARIO_PRINCIPAL") or "8418729793"
    return str(usuario_id)


def _safe_str(val) -> str:
    return str(val) if val is not None else ""


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto: convierte a minúsculas, elimina acentos y espacios extra.
    
    Args:
        texto: Texto a normalizar
        
    Returns:
        Texto normalizado (minúsculas, sin acentos, espacios simples)
    """
    if not texto:
        return ""
    
    # Convertir a string y hacer strip
    texto = str(texto).strip()
    
    # Convertir a minúsculas
    texto = texto.lower()
    
    # Eliminar acentos usando normalización Unicode
    import unicodedata
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    
    # Normalizar espacios múltiples a uno solo
    texto = ' '.join(texto.split())
    
    return texto


def _fmt_cop(monto: float) -> str:
    """Formatea un monto en COP con separador de miles."""
    return f"${monto:,.0f} COP"


# ---------------------------------------------------------------------------
# Definición de herramientas
# ---------------------------------------------------------------------------


def _obtener_balance(usuario_id: str) -> str:
    """Suma los saldos de users/{usuario_id}/accounts (colección Kebo, no 'cuentas')."""
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    logger.info("Consultando Firestore para el usuario: %s", usuario_id)
    from modules.finance.accounts import listar_cuentas

    cuentas = listar_cuentas(usuario_id)
    if not cuentas:
        return (
            f"No se encontraron cuentas en users/{usuario_id}/accounts. "
            "El balance es $0 COP."
        )
    total = sum(float(c.get("balance", 0) or 0) for c in cuentas)
    lines = [f"Balance total de {usuario_id}: {_fmt_cop(total)}"]
    for c in cuentas:
        lines.append(
            f"  • {c['nombre']} ({c.get('type', 'cash')}) — {_fmt_cop(float(c.get('balance', 0) or 0))}"
        )
    return "\n".join(lines)


def _obtener_balance_consolidado(usuario_id: str) -> str:
    """Calcula el balance consolidado sumando las cuentas raíz: Nu, Nequi y Efectivo."""
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    logger.info("Calculando balance consolidado para el usuario: %s", usuario_id)
    from modules.finance.accounts import listar_cuentas

    cuentas = listar_cuentas(usuario_id)
    if not cuentas:
        return (
            f"No se encontraron cuentas en la colección raíz 'accounts' para el usuario {usuario_id}. "
            "El balance consolidado es $0 COP."
        )
    
    # Filtrar solo las cuentas principales: Nu, Nequi, Efectivo
    cuentas_principales = []
    nombres_principales = {'nu', 'nequi', 'efectivo'}
    from src.agent.tools import _normalizar_texto
    for cuenta in cuentas:
        nombre_norm = _normalizar_texto(cuenta['nombre'])
        if nombre_norm in nombres_principales:
            cuentas_principales.append(cuenta)
    
    if not cuentas_principales:
        return (
            f"No se encontraron las cuentas principales (Nu, Nequi, Efectivo) para el usuario {usuario_id}. "
            "Se encontraron {len(cuentas)} cuentas pero ninguna coincide con las principales."
        )
    
    total = sum(float(cuenta.get("balance", 0) or 0) for cuenta in cuentas_principales)
    lines = [f"Balance consolidado de {usuario_id} (Nu + Nequi + Efectivo): {_fmt_cop(total)}"]
    for cuenta in cuentas_principales:
        lines.append(
            f"  • {cuenta['nombre']} ({cuenta.get('type', 'cash')}) — {_fmt_cop(float(cuenta.get('balance', 0) or 0))}"
        )
    return "\n".join(lines)


def _generar_recomendaciones_inversion(usuario_id: str) -> str:
    """Genera recomendaciones personalizadas de inversión basado en el balance consolidado y perfil."""
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    logger.info("Generando recomendaciones de inversión para el usuario: %s", usuario_id)
    
    # Obtener el balance consolidado primero
    balance_result = _obtener_balance_consolidado(usuario_id)
    
    # Extraer el valor numérico del balance (asumiendo formato conocido)
    import re
    balance_match = re.search(r'\$\s*([\d,]+\.?\d*)\s*COP', balance_result)
    if not balance_match:
        return "No se pudo determinar el balance consolidado para generar recomendaciones."
    
    balance_str = balance_match.group(1).replace(',', '')
    try:
        balance = float(balance_str)
    except ValueError:
        return "Error al procesar el valor del balance consolidado."
    
    # Lógica de recomendaciones basada en el balance
    if balance < 1000000:  # Menos de 1 millón COP
        recomendacion = """Estrategia Conservadora:
- Fondo de emergencia: Priorizar completar 3-6 meses de gastos básicos
- Inversión inicial: Considerar CDT o cuentas de ahorro de alto rendimiento
- Educación: Asignar recursos para aprender sobre finanzas personales"""
    elif balance < 5000000:  # Entre 1 y 5 millones COP
        recomendacion = """Estrategia Moderada:
- Fondo de emergencia: Mantener 3-6 meses de gastos en cuenta de ahorro
- Inversión diversificada: 70% en instrumentos de renta fija, 30% en fondos de inversión
- Objetivo medio plazo: Considerar inversión en bienes raíces o negocios"""
    else:  # Más de 5 millones COP
        recomendacion = """Estrategia Agresiva:
- Fondo de emergencia: Completado, mantener liquidez para oportunidades
- Inversión diversificada: 50% renta variable, 30% renta fija, 20% alternativas
- Objetivo largo plazo: Considerar inversiones en acciones, bienes raíces y proyectos empresariales"""
    
    lines = [
        f"Recomendaciones de inversión para balance de {_fmt_cop(balance)}:",
        "",
        recomendacion,
        "",
        "Nota: Estas son sugerencias generales. Consulte con un asesor financiero para recomendaciones personalizadas."
    ]
    return "\n".join(lines)


TOOL_OBTENER_BALANCE_CONSOLIDADO = AgentTool(
    nombre="obtener_balance_consolidado",
    descripcion=(
        "Calcula el balance consolidado sumando específicamente las cuentas de Nu, Nequi y Efectivo "
        "de la colección raíz 'accounts' en Firestore."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {
                "type": "string",
                "description": "ID único del usuario en Firestore.",
            }
        },
        "required": ["usuario_id"],
    },
    funcion=_obtener_balance_consolidado,
)

TOOL_GENERAR_RECOMENDACIONES_INVERSION = AgentTool(
    nombre="generar_recomendaciones_inversion",
    descripcion=(
        "Genera recomendaciones personalizadas de inversión basado en el balance consolidado "
        "y perfil financiero del usuario, incluyendo estrategias de pago de deudas, ahorro e inversión."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {
                "type": "string",
                "description": "ID único del usuario en Firestore.",
            }
        },
        "required": ["usuario_id"],
    },
    funcion=_generar_recomendaciones_inversion,
)


def _listar_cuentas(usuario_id: str) -> str:
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    logger.info("Consultando Firestore para el usuario: %s", usuario_id)
    from modules.finance.accounts import listar_cuentas
    cuentas = listar_cuentas(usuario_id)
    if not cuentas:
        return "No se encontraron cuentas registradas."
    lines = [f"💰 Cuentas de {usuario_id}:"]
    for c in cuentas:
        lines.append(
            f"  • {c['nombre']} ({c.get('type','cash')}) — Balance: {_fmt_cop(float(c.get('balance',0)))}"
        )
    return "\n".join(lines)


TOOL_LISTAR_CUENTAS = AgentTool(
    nombre="listar_cuentas",
    descripcion="Lista todas las cuentas financieras del usuario con sus saldos actuales.",
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
        },
        "required": ["usuario_id"],
    },
    funcion=_listar_cuentas,
)


def _registrar_transaccion(
    usuario_id: str,
    tipo: str,
    monto: float,
    categoria: str,
    descripcion: str = "",
    cuenta: str = "Efectivo",
    fecha: Optional[str] = None,
) -> str:
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    from modules.finance.transactions.create import registrar_transaccion_v2
    tx_id = registrar_transaccion_v2(
        usuario_id=usuario_id,
        tipo=tipo,
        monto=float(monto),
        categoria_nombre=categoria,
        descripcion=descripcion,
        cuenta_nombre=cuenta,
        fecha=fecha,
    )
    if tx_id:
        signo = "+" if tipo == "income" else "-"
        return (
            f"✅ Transacción registrada (ID: {tx_id})\n"
            f"   {signo}{_fmt_cop(float(monto))} en '{categoria}' — {descripcion or 'Sin descripción'}"
        )
    return "❌ No se pudo registrar la transacción. Verifica los datos e intenta de nuevo."


TOOL_REGISTRAR_TRANSACCION = AgentTool(
    nombre="registrar_transaccion",
    descripcion=(
        "Registra un ingreso o gasto en la cuenta del usuario. "
        "Usa tipo='income' para ingresos y tipo='expense' para gastos."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
            "tipo": {
                "type": "string",
                "enum": ["income", "expense"],
                "description": "Tipo de transacción: 'income' (ingreso) o 'expense' (gasto).",
            },
            "monto": {"type": "number", "description": "Monto en COP (positivo)."},
            "categoria": {"type": "string", "description": "Nombre de la categoría."},
            "descripcion": {"type": "string", "description": "Descripción opcional del movimiento."},
            "cuenta": {
                "type": "string",
                "description": "Nombre de la cuenta. Por defecto 'Efectivo'.",
            },
            "fecha": {
                "type": "string",
                "description": "Fecha en formato YYYY-MM-DD. Si se omite, usa la fecha actual.",
            },
        },
        "required": ["usuario_id", "tipo", "monto", "categoria"],
    },
    funcion=_registrar_transaccion,
)


def _listar_transacciones(usuario_id: str, periodo: Optional[str] = None) -> str:
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    from modules.firestore.client import _get_user_ref
    periodo = periodo or _periodo_actual()
    _, user_ref = _get_user_ref(usuario_id)
    if not user_ref:
        return "❌ No se pudo conectar con la base de datos."
    try:
        docs = (
            user_ref.collection("transactions")
            .document(periodo)
            .collection("items")
            .stream()
        )
        transacciones = [d.to_dict() or {} for d in docs]
    except Exception as exc:
        logger.error("Error listando transacciones: %s", exc)
        return f"❌ Error consultando transacciones de {periodo}."
    
    if not transacciones:
        return f"No hay transacciones registradas para el periodo {periodo}."
    lines = [f"📋 Últimas transacciones ({periodo}):"]
    for t in transacciones[-10:]:
        tipo_emoji = "📈" if t.get("type") == "income" else "📉"
        monto = float(t.get("amount", t.get("monto", 0)))
        cat = t.get("category_name", t.get("categoria", "General"))
        desc = t.get("description", t.get("descripcion", ""))
        lines.append(f"  {tipo_emoji} {_fmt_cop(monto)} — {cat}{' | ' + desc if desc else ''}")
    return "\n".join(lines)


TOOL_LISTAR_TRANSACCIONES = AgentTool(
    nombre="listar_transacciones",
    descripcion=(
        "Lista las transacciones recientes del usuario. "
        "Si no se indica periodo, usa el mes actual (YYYY-MM)."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
            "periodo": {
                "type": "string",
                "description": "Periodo en formato YYYY-MM. Si se omite, usa el mes actual.",
            },
        },
        "required": ["usuario_id"],
    },
    funcion=_listar_transacciones,
)


def _obtener_presupuestos(usuario_id: str, periodo: Optional[str] = None) -> str:
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    logger.info("Consultando Firestore para el usuario: %s", usuario_id)
    from modules.finance.budgets.retrieve import obtener_presupuestos_mes
    periodo = periodo or _periodo_actual()
    year, month = periodo.split("-")
    presupuestos = obtener_presupuestos_mes(usuario_id, year=year, month=month)
    if not presupuestos:
        return f"No hay presupuestos definidos para {periodo}."
    lines = [f"📊 Presupuestos de {periodo}:"]
    for nombre, info in presupuestos.items():
        limite = float(info.get("limite", 0))
        gastado = float(info.get("gastado", 0))
        restante = limite - gastado
        pct = (gastado / limite * 100) if limite > 0 else 0
        estado = "⚠️" if pct >= 90 else "✅"
        lines.append(
            f"  {estado} {nombre}: Límite {_fmt_cop(limite)} | "
            f"Gastado {_fmt_cop(gastado)} ({pct:.0f}%) | Restante {_fmt_cop(restante)}"
        )
    return "\n".join(lines)


TOOL_OBTENER_PRESUPUESTOS = AgentTool(
    nombre="obtener_presupuestos",
    descripcion=(
        "Obtiene los presupuestos mensuales del usuario con su progreso (gastado vs límite). "
        "Un presupuesto es un techo de gasto, no dinero separado."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
            "periodo": {
                "type": "string",
                "description": "Periodo en formato YYYY-MM. Si se omite, usa el mes actual.",
            },
        },
        "required": ["usuario_id"],
    },
    funcion=_obtener_presupuestos,
)


def _establecer_presupuesto(
    usuario_id: str,
    categoria: str,
    monto: float,
    periodo: Optional[str] = None,
) -> str:
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    from modules.finance.budgets.create import establecer_presupuesto_mes
    periodo = periodo or _periodo_actual()
    year, month = periodo.split("-")
    ok = establecer_presupuesto_mes(
        usuario_id=usuario_id,
        categoria_nombre=categoria,
        monto=float(monto),
        year=year,
        month=month,
    )
    if ok:
        return f"✅ Presupuesto de '{categoria}' establecido en {_fmt_cop(float(monto))} para {periodo}."
    return f"❌ No se pudo establecer el presupuesto de '{categoria}'."


TOOL_ESTABLECER_PRESUPUESTO = AgentTool(
    nombre="establecer_presupuesto",
    descripcion=(
        "Crea o actualiza el presupuesto mensual de una categoría. "
        "El monto es el techo máximo de gasto mensual para esa categoría."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
            "categoria": {"type": "string", "description": "Nombre de la categoría."},
            "monto": {"type": "number", "description": "Techo de gasto mensual en COP."},
            "periodo": {
                "type": "string",
                "description": "Periodo en formato YYYY-MM. Si se omite, usa el mes actual.",
            },
        },
        "required": ["usuario_id", "categoria", "monto"],
    },
    funcion=_establecer_presupuesto,
)


def _listar_recordatorios(usuario_id: str) -> str:
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    from modules.reminders.service import listar_recordatorios
    recordatorios = listar_recordatorios(usuario_id)
    if not recordatorios:
        return "No hay recordatorios activos."
    lines = ["🔔 Recordatorios activos:"]
    for r in recordatorios:
        texto = r.get("text", r.get("texto", ""))
        dia = r.get("day", r.get("dia", "?"))
        month = r.get("month", "")
        year = r.get("year", "")
        monto = float(r.get("monto", 0))
        fecha_str = f"{year}-{month}-{dia:02d}" if month and year else f"día {dia}"
        monto_str = f" | {_fmt_cop(monto)}" if monto else ""
        lines.append(f"  • {texto} — {fecha_str}{monto_str}")
    return "\n".join(lines)


TOOL_LISTAR_RECORDATORIOS = AgentTool(
    nombre="listar_recordatorios",
    descripcion="Lista todos los recordatorios activos del usuario.",
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
        },
        "required": ["usuario_id"],
    },
    funcion=_listar_recordatorios,
)


def _guardar_recordatorio(
    usuario_id: str,
    texto: str,
    dia: int,
    categoria: str = "",
    monto: float = 0,
) -> str:
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    from modules.reminders.service import guardar_recordatorio
    rec_id = guardar_recordatorio(
        usuario_id=usuario_id,
        texto=texto,
        dia=int(dia),
        categoria=categoria,
        monto=float(monto),
    )
    if rec_id:
        return f"✅ Recordatorio creado: '{texto}' para el día {dia}{' — ' + _fmt_cop(float(monto)) if monto else ''}."
    return "❌ No se pudo crear el recordatorio."


TOOL_GUARDAR_RECORDATORIO = AgentTool(
    nombre="guardar_recordatorio",
    descripcion="Crea un recordatorio de pago o actividad para un día del mes.",
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
            "texto": {"type": "string", "description": "Descripción del recordatorio (ej: 'Pagar arriendo')."},
            "dia": {"type": "integer", "description": "Día del mes (1-31)."},
            "categoria": {"type": "string", "description": "Categoría asociada (opcional)."},
            "monto": {"type": "number", "description": "Monto asociado en COP (opcional)."},
        },
        "required": ["usuario_id", "texto", "dia"],
    },
    funcion=_guardar_recordatorio,
)


def _obtener_contexto_financiero(usuario_id: str) -> str:
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    from modules.finance.legacy import obtener_contexto_financiero
    return obtener_contexto_financiero(usuario_id)


TOOL_CONTEXTO_FINANCIERO = AgentTool(
    nombre="obtener_contexto_financiero",
    descripcion=(
        "Obtiene un resumen financiero completo del usuario: liquidez de cuentas, "
        "movimientos del mes actual, presupuestos con progreso e histórico. "
        "Úsala antes de responder preguntas financieras complejas."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
        },
        "required": ["usuario_id"],
    },
    funcion=_obtener_contexto_financiero,
)


def _guardar_skill(usuario_id: str, nombre: str, contenido: str, tipo: str = "preferencia") -> str:
    """Guarda una habilidad/preferencia en la colección 'skills' de Firestore."""
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    from modules.firestore.client import _get_user_ref, get_db
    from modules.firestore.client import firestore as fs

    db = get_db()
    if not db:
        return "❌ No se pudo conectar con la base de datos."
    try:
        # Normalizar el nombre para evitar duplicados por mayúsculas/minúsculas/acentos
        nombre_normalizado = _normalizar_texto(nombre)
        # Verificar si ya existe una skill con este nombre normalizado
        _, user_ref = _get_user_ref(usuario_id)
        if user_ref:
            skills_existentes = user_ref.collection("skills").stream()
            for skill_doc in skills_existentes:
                skill_data = skill_doc.to_dict()
                if skill_data and _normalizar_texto(skill_data.get("nombre", "")) == nombre_normalizado:
                    # Actualizar la skill existente en lugar de crear una nueva
                    skill_doc.reference.update({
                        "contenido": contenido,
                        "tipo": tipo,
                        "created_at": fs.SERVER_TIMESTAMP,
                    })
                    return f"✅ Habilidad '{nombre}' actualizada exitosamente (evitando duplicado)."
        
        # Si no existe, crear nueva skill
        skill_ref = db.collection("skills").document()
        skill_ref.set({
            "nombre": nombre,
            "contenido": contenido,
            "tipo": tipo,
            "created_at": fs.SERVER_TIMESTAMP,
        })
        return f"✅ Habilidad '{nombre}' guardada exitosamente."
    except Exception as exc:
        logger.error("Error guardando skill: %s", exc)
        return f"❌ Error guardando habilidad: {exc}"


TOOL_GUARDAR_SKILL = AgentTool(
    nombre="guardar_skill",
    descripcion=(
        "Guarda una regla, preferencia o acuerdo financiero del usuario en Firestore "
        "para que JARVIS lo recuerde en futuras conversaciones."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
            "nombre": {"type": "string", "description": "Nombre corto de la habilidad/regla."},
            "contenido": {"type": "string", "description": "Descripción completa de la regla o preferencia."},
            "tipo": {
                "type": "string",
                "enum": ["preferencia", "regla", "acuerdo", "meta"],
                "description": "Categoría de la habilidad.",
            },
        },
        "required": ["usuario_id", "nombre", "contenido"],
    },
    funcion=_guardar_skill,
)


def _listar_skills(usuario_id: str) -> str:
    """Lista las habilidades/preferencias guardadas del usuario."""
    if not usuario_id or usuario_id in ['usuario_1234', 'user_1234', 'default']:
        usuario_id = os.getenv('DEFAULT_USER_ID') or os.getenv('USUARIO_PRINCIPAL') or '8418729793'
    from modules.firestore.client import _get_user_ref, get_db
    db = get_db()
    if not db:
        return "❌ No se pudo conectar con la base de datos."
    try:
        docs = list(db.collection("skills").stream())
        if not docs:
            return "No hay habilidades guardadas aún."
        lines = ["🧠 Habilidades/preferencias guardadas:"]
        for d in docs:
            data = d.to_dict()
            lines.append(
                f"  • [{data.get('tipo','?')}] {data.get('nombre','?')}: {data.get('contenido','')}"
            )
        return "\n".join(lines)
    except Exception as exc:
        logger.error("Error listando skills: %s", exc)
        return f"❌ Error leyendo habilidades: {exc}"


TOOL_LISTAR_SKILLS = AgentTool(
    nombre="listar_skills",
    descripcion=(
        "Lista todas las reglas, preferencias y acuerdos financieros que el usuario "
        "ha guardado previamente. Úsala al inicio de la conversación para personalizar las respuestas."
    ),
    parametros={
        "type": "object",
        "properties": {
            "usuario_id": {"type": "string", "description": "ID único del usuario."},
        },
        "required": ["usuario_id"],
    },
    funcion=_listar_skills,
)


# ---------------------------------------------------------------------------
# Registro global de herramientas
# ---------------------------------------------------------------------------

ALL_TOOLS: List[AgentTool] = [
    TOOL_CONTEXTO_FINANCIERO,
    TOOL_OBTENER_BALANCE_CONSOLIDADO,
    TOOL_LISTAR_CUENTAS,
    TOOL_REGISTRAR_TRANSACCION,
    TOOL_LISTAR_TRANSACCIONES,
    TOOL_OBTENER_PRESUPUESTOS,
    TOOL_ESTABLECER_PRESUPUESTO,
    TOOL_LISTAR_RECORDATORIOS,
    TOOL_GUARDAR_RECORDATORIO,
    TOOL_GUARDAR_SKILL,
    TOOL_LISTAR_SKILLS,
    TOOL_OBTENER_BALANCE_CONSOLIDADO,
    TOOL_GENERAR_RECOMENDACIONES_INVERSION,
]

TOOLS_BY_NAME: Dict[str, AgentTool] = {t.nombre: t for t in ALL_TOOLS}
