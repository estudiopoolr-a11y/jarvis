"""
src/agent/hermes_engine.py — Motor agéntico Hermes para JARVIS.

Implementa el patrón ReAct (Reason → Act → Observe) con auto-corrección:
  1. Carga personalidad desde SOUL.md y habilidades desde Firestore (skills).
  2. Registra las herramientas disponibles (Firestore: cuentas, transacciones,
     presupuestos, recordatorios, habilidades).
  3. Bucle ReAct: el LLM decide qué herramientas invocar antes de responder.
  4. Auto-corrección: captura excepciones, las reenvía al LLM y reintenta
     hasta MAX_RETRIES veces antes de responder con el error.

REGLAS AGENTS.md:
  - Nunca reemplaza parsers determinísticos de modules/ai.py.
  - Solo es invocado si ningún parser coincide (fallback generativo).
  - Las mutaciones de Firestore se realizan via herramientas (tools), con
    flujo explícito controlado, no autónomamente por el LLM.
  - Nunca guarda credenciales ni tokens.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from src.agent.tools import ALL_TOOLS, TOOLS_BY_NAME, AgentTool, _normalizar_texto
from src.core.llm_provider import LLMMessage, LLMResponse, get_llm_provider

logger = logging.getLogger("JARVIS.hermes")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MAX_REACT_ITERATIONS = 6   # Máximo de ciclos Reason→Act en una sola petición
MAX_RETRIES = 3             # Reintentos en auto-corrección por herramienta
SOUL_PATH = Path(__file__).parents[2] / "SOUL.md"  # Raíz del proyecto / SOUL.md
_IDS_INVALIDOS = {"usuario_1234", "user_1234", "default", "none", "null", ""}


def _usuario_real(usuario_id: Optional[str] = None) -> str:
    """Reemplaza IDs de prueba, vacíos o None por el usuario real de la petición."""
    candidato = "" if usuario_id is None else str(usuario_id).strip()
    if candidato.lower() in _IDS_INVALIDOS:
        return (
            os.getenv("DEFAULT_USER_ID")
            or os.getenv("USUARIO_PRINCIPAL")
            or "8418729793"
        )
    return candidato


def _sanitizar_args_usuario(args: Dict, usuario_id: str) -> Dict:
    """Reemplaza usuario_1234, user_1234, default, None o vacío por el user_id real."""
    limpios = dict(args or {})
    real = _usuario_real(usuario_id)
    for clave in ("usuario_id", "user_id"):
        if clave in limpios:
            limpios[clave] = _usuario_real(limpios.get(clave) or real)
    for clave, valor in list(limpios.items()):
        if str(valor).strip().lower() in {"usuario_1234", "user_1234", "default"}:
            limpios[clave] = real
    return limpios


# ---------------------------------------------------------------------------
# Carga de personalidad
# ---------------------------------------------------------------------------

_soul_cache: Optional[str] = None


def _cargar_soul() -> str:
    """Lee SOUL.md y cachea el contenido en memoria."""
    global _soul_cache
    if _soul_cache is None:
        try:
            _soul_cache = SOUL_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("SOUL.md no encontrado en %s. Usando instrucción mínima.", SOUL_PATH)
            _soul_cache = (
                "Eres JARVIS, un asistente financiero personal inteligente. "
                "Responde en español de forma directa y amable."
            )
    return _soul_cache


# ---------------------------------------------------------------------------
# Carga de skills desde Firestore
# ---------------------------------------------------------------------------

async def _cargar_skills(usuario_id: str) -> str:
    """
    Carga habilidades/preferencias del usuario desde Firestore (colección 'skills').
    Retorna una cadena formateada para incluir en el system prompt.
    """
    try:
        from modules.firestore.client import _get_user_ref

        loop = asyncio.get_event_loop()

        def _fetch():
            _, user_ref = _get_user_ref(usuario_id)
            if not user_ref:
                return []
            return [d.to_dict() for d in user_ref.collection("skills").stream()]

        skills = await loop.run_in_executor(None, _fetch)
        if not skills:
            return ""

        # Normalizar nombres de skills para evitar duplicados por mayúsculas/minúsculas/acentos
        skills_normalizadas = {}
        for s in skills:
            nombre_original = s.get("nombre", "")
            nombre_normalizado = _normalizar_texto(nombre_original)
            # Si ya existe una skill con este nombre normalizado, la sobrescribimos (manteniendo la última)
            if nombre_normalizado in skills_normalizadas:
                logger.warning("Skill duplicada detectada (normalizada): '%s' -> '%s'", nombre_original, nombre_normalizado)
            skills_normalizadas[nombre_normalizado] = s

        lines = ["\n## Preferencias y reglas del usuario (Skills guardados):"]
        for s in skills_normalizadas.values():
            tipo = s.get("tipo", "preferencia")
            nombre = s.get("nombre", "")
            contenido = s.get("contenido", "")
            lines.append(f"- [{tipo}] {nombre}: {contenido}")
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("No se pudieron cargar skills: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Motor principal: HermesAgent
# ---------------------------------------------------------------------------


class HermesAgent:
    """
    Agente autónomo JARVIS basado en el patrón ReAct.

    Uso:
        agent = HermesAgent()
        respuesta = await agent.process_message("¿Cuánto gasté este mes?", "12345")
    """

    def __init__(self, tools: Optional[List[AgentTool]] = None):
        self._tools = tools or ALL_TOOLS
        self._llm = get_llm_provider()
        self._tool_declarations = [t.to_function_declaration() for t in self._tools]

    def _build_system_prompt(self, skills_context: str = "", usuario_id: str = "") -> str:
        """Construye el system prompt completo: SOUL + skills del usuario + fecha actual."""
        soul = _cargar_soul()
        prompt = soul
        if skills_context:
            prompt += "\n\n" + skills_context
        # Inyectar fecha actual para que el agente conozca el contexto temporal
        from datetime import datetime
        fecha_actual = datetime.now().strftime("%Y-%m-%d (%B %Y)")
        prompt += (
            f"\n\n## Contexto temporal:\n"
            f"La fecha actual del sistema es {fecha_actual}. Usa este año y mes como referencia para 'este mes', 'mes actual' o consultas relativas.\n"
            "\n\n## Instrucciones de operación:\n"
            "Tienes acceso a herramientas para consultar y modificar los datos financieros del usuario. "
            "Usa las herramientas cuando necesites datos concretos antes de responder. "
            "Si ya tienes suficiente contexto, responde directamente sin llamar herramientas. "
            "Siempre distingue entre: liquidez de cuentas, presupuestos (techos de gasto) e histórico. "
            "Responde en español. Sé conciso: máximo 3 párrafos salvo análisis complejos."
        )
        return prompt

    async def _ejecutar_herramienta_con_retry(
        self,
        tool: AgentTool,
        args: Dict,
        usuario_id: str,
        historial: List[LLMMessage],
        system_prompt: str,
    ) -> str:
        """
        Ejecuta una herramienta con auto-corrección.
        Si falla, inyecta el error en el historial y pide al LLM que reintente
        con argumentos corregidos (hasta MAX_RETRIES veces).
        """
        ultimo_error: Optional[Exception] = None

        for intento in range(1, MAX_RETRIES + 1):
            try:
                args = _sanitizar_args_usuario(args, usuario_id)
                if "usuario_id" in tool.parametros.get("properties", {}):
                    args["usuario_id"] = _usuario_real(args.get("usuario_id") or usuario_id)
                loop = asyncio.get_event_loop()
                # Ejecutar en executor (las funciones de Firestore son síncronas)
                resultado = await loop.run_in_executor(
                    None, lambda a=args: tool.ejecutar(**a)
                )
                if intento > 1:
                    logger.info(
                        "Herramienta '%s' exitosa en intento %d.", tool.nombre, intento
                    )
                return resultado

            except Exception as exc:
                ultimo_error = exc
                logger.warning(
                    "Herramienta '%s' falló (intento %d/%d): %s",
                    tool.nombre,
                    intento,
                    MAX_RETRIES,
                    exc,
                )
                if intento < MAX_RETRIES:
                    # Inyectar el error en el historial para que el LLM corrija
                    error_msg = (
                        f"La herramienta '{tool.nombre}' falló con el error: {exc}. "
                        f"Por favor, corrige los argumentos e intenta de nuevo."
                    )
                    historial.append(
                        LLMMessage(role="user", content=f"[ERROR DE HERRAMIENTA] {error_msg}")
                    )
                    # Pedir al LLM una corrección
                    try:
                        correccion: LLMResponse = await self._llm.generate(
                            messages=historial,
                            system_prompt=system_prompt,
                            max_tokens=512,
                            tools=self._tool_declarations,
                        )
                        # Si el LLM sugiere nuevos tool_calls, actualizar args
                        if correccion.tool_calls:
                            for tc in correccion.tool_calls:
                                if tc.get("name") == tool.nombre:
                                    args = _sanitizar_args_usuario(tc.get("args", args), usuario_id)
                                    break
                        historial.append(
                            LLMMessage(role="assistant", content=correccion.text or "")
                        )
                    except Exception as llm_exc:
                        logger.warning("LLM no pudo sugerir corrección: %s", llm_exc)

        return (
            f"⚠️ La herramienta '{tool.nombre}' falló después de {MAX_RETRIES} intentos. "
            f"Último error: {ultimo_error}"
        )

    async def process_message(
        self,
        texto: str,
        usuario_id: str,
        historial_previo: Optional[List[LLMMessage]] = None,
    ) -> str:
        """
        Procesa un mensaje del usuario mediante el bucle ReAct.

        Args:
            texto: Mensaje del usuario.
            usuario_id: ID del usuario en Firestore.
            historial_previo: Historial de conversación previo (opcional).

        Returns:
            Respuesta final del agente como texto.
        """
        # Normalizar usuario_id si es genérico, de prueba o vacío
        usuario_id = _usuario_real(usuario_id)

        logger.info("HermesAgent procesando mensaje de usuario=%s", usuario_id)

        # 1. Cargar contexto: skills del usuario
        skills_context = await _cargar_skills(usuario_id)

        # 2. Construir system prompt
        system_prompt = self._build_system_prompt(skills_context)

        # 3. Inicializar historial con el mensaje actual
        historial: List[LLMMessage] = list(historial_previo or [])
        historial.append(LLMMessage(role="user", content=texto))

        # 4. Bucle ReAct
        for iteracion in range(MAX_REACT_ITERATIONS):
            logger.debug("ReAct iteración %d/%d", iteracion + 1, MAX_REACT_ITERATIONS)

            try:
                respuesta: LLMResponse = await self._llm.generate(
                    messages=historial,
                    system_prompt=system_prompt,
                    max_tokens=2048,
                    tools=self._tool_declarations,
                )
            except Exception as exc:
                logger.error("Error llamando al LLM: %s", exc, exc_info=True)
                return (
                    f"⚠️ No pude procesar tu solicitud en este momento. "
                    f"Por favor, inténtalo de nuevo en unos segundos.\n"
                    f"_(Error: {exc})_"
                )

            # 4a. Sin tool_calls → respuesta final
            if not respuesta.tool_calls:
                texto_final = respuesta.text or "Sin respuesta disponible."
                logger.info(
                    "ReAct completado en %d iteración(es) via %s.",
                    iteracion + 1,
                    respuesta.provider,
                )
                return texto_final

            # 4b. Con tool_calls → ejecutar herramientas
            # Registrar el turno del asistente en el historial
            historial.append(
                LLMMessage(role="assistant", content=respuesta.text or "")
            )

            # Ejecutar cada herramienta solicitada
            observaciones: List[str] = []
            for tool_call in respuesta.tool_calls:
                tool_nombre = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", tool_nombre)

                tool = TOOLS_BY_NAME.get(tool_nombre)
                if not tool:
                    obs = f"❌ Herramienta desconocida: '{tool_nombre}'."
                    logger.warning("Herramienta no encontrada: %s", tool_nombre)
                else:
                    tool_args = _sanitizar_args_usuario(tool_args, usuario_id)
                    if "usuario_id" in tool.parametros.get("properties", {}):
                        tool_args["usuario_id"] = _usuario_real(
                            tool_args.get("usuario_id") or usuario_id
                        )

                    logger.info("Ejecutando herramienta: %s(%s)", tool_nombre, tool_args)
                    obs = await self._ejecutar_herramienta_con_retry(
                        tool=tool,
                        args=tool_args,
                        usuario_id=usuario_id,
                        historial=historial,
                        system_prompt=system_prompt,
                    )

                observaciones.append(f"[{tool_nombre}]: {obs}")
                # Agregar resultado al historial como mensaje de tool
                historial.append(
                    LLMMessage(
                        role="tool",
                        content=obs,
                        tool_call_id=tool_id,
                        name=tool_nombre,
                    )
                )

            logger.debug(
                "Observaciones de herramientas: %s", "; ".join(observaciones[:3])
            )
            # El bucle continuará y el LLM procesará las observaciones

        # 5. Fallback si se agotaron las iteraciones
        logger.warning("ReAct agotó %d iteraciones sin respuesta final.", MAX_REACT_ITERATIONS)
        return (
            "Procesé tu solicitud pero el análisis requirió demasiados pasos. "
            "Por favor, reformula tu pregunta de forma más específica."
        )


# ---------------------------------------------------------------------------
# Instancia singleton
# ---------------------------------------------------------------------------

_hermes_agent: Optional[HermesAgent] = None


def get_hermes_agent() -> HermesAgent:
    """Retorna la instancia singleton de HermesAgent."""
    global _hermes_agent
    if _hermes_agent is None:
        _hermes_agent = HermesAgent()
    return _hermes_agent
