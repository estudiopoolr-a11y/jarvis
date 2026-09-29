"""
src/core/llm_provider.py — Cliente LLM unificado con soporte para Gemini y Nvidia NIM.

Permite alternar o usar fallback entre:
  - Google Gemini  (GEMINI_API_KEY / GEMINI_API_KEYS)
  - Nvidia NIM / OpenAI-compatible  (NVIDIA_API_KEY + NVIDIA_BASE_URL)

Diseño:
  - LLMMessage: dataclass de intercambio (role, content)
  - GeminiProvider: wrapper asíncrono sobre modules.gemini.client
  - NvidiaProvider: wrapper asíncrono sobre la API compatible con OpenAI
  - LLMProvider: orquestador con fallback automático entre proveedores

Restricción JARVIS: Este módulo es de SOLO LECTURA para el LLM.
Las mutaciones de Firestore siempre ocurren por flujo determinístico.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("JARVIS.llm_provider")


# ---------------------------------------------------------------------------
# Tipos comunes
# ---------------------------------------------------------------------------

@dataclass
class LLMMessage:
    """Mensaje de intercambio entre agente y LLM."""
    role: str   # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Respuesta normalizada del LLM."""
    text: str
    provider: str
    tool_calls: List[dict] = field(default_factory=list)
    raw: Optional[object] = None


# ---------------------------------------------------------------------------
# Provider: Google Gemini
# ---------------------------------------------------------------------------

class GeminiProvider:
    """
    Proveedor de Gemini usando el cliente existente en modules.gemini.client.
    Reutiliza la rotación de keys y el rate limiter ya implementados.
    """

    NAME = "gemini"

    def __init__(self):
        self._ready: Optional[bool] = None

    def _check_ready(self) -> bool:
        if self._ready is None:
            api_keys = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY", "")
            self._ready = bool(api_keys.strip())
        return self._ready

    async def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: str = "",
        max_tokens: int = 2048,
        tools: Optional[List[dict]] = None,
    ) -> LLMResponse:
        """Llama a Gemini de forma asíncrona usando el cliente compartido."""
        if not self._check_ready():
            raise RuntimeError("GEMINI_API_KEY no configurado.")

        # Importar dentro de función para respetar regla de AGENTS.md sobre imports
        # y para no fallar al importar el módulo si la key no está disponible.
        from modules.gemini.client import MODEL_NAME, _gemini_call_with_fallback
        from google.genai import types

        # Construir prompt completo: system + historial de mensajes
        history_parts = []
        if system_prompt:
            history_parts.append(f"[SISTEMA]\n{system_prompt}")

        for msg in messages:
            role_label = {"user": "Usuario", "assistant": "JARVIS", "tool": "Tool"}.get(
                msg.role, msg.role.capitalize()
            )
            history_parts.append(f"[{role_label}]\n{msg.content}")

        full_prompt = "\n\n".join(history_parts)

        # Ejecutar en executor para no bloquear el event loop (la llamada es síncrona)
        loop = asyncio.get_event_loop()
        gemini_tools = None
        if tools:
            # Herramientas en formato Gemini (function declarations)
            gemini_tools = [{"function_declarations": tools}]

        def _call(client):
            config_kwargs = {
                "max_output_tokens": max_tokens,
                "safety_settings": [
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
            }
            if gemini_tools:
                config_kwargs["tools"] = gemini_tools

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=full_prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            return response

        response = await loop.run_in_executor(
            None, lambda: _gemini_call_with_fallback(_call)
        )

        # Extraer tool_calls si los hay
        tool_calls = []
        text = ""
        try:
            # Intentar extraer function calls de la respuesta
            for candidate in (response.candidates or []):
                for part in (candidate.content.parts if candidate.content else []):
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        tool_calls.append({
                            "name": fc.name,
                            "args": dict(fc.args) if fc.args else {},
                        })
                    elif hasattr(part, "text") and part.text:
                        text += part.text
        except Exception:
            # Fallback: usar .text directamente
            text = getattr(response, "text", str(response)) or ""

        if not text and not tool_calls:
            text = getattr(response, "text", "") or "Sin respuesta."

        return LLMResponse(
            text=text.strip(),
            provider=self.NAME,
            tool_calls=tool_calls,
            raw=response,
        )


# ---------------------------------------------------------------------------
# Provider: Nvidia NIM / OpenAI-compatible
# ---------------------------------------------------------------------------

class NvidiaProvider:
    """
    Proveedor Nvidia NIM usando la API compatible con OpenAI (openai SDK).
    Variables de entorno:
      NVIDIA_API_KEY   → Bearer token
      NVIDIA_BASE_URL  → https://integrate.api.nvidia.com/v1
      NVIDIA_MODEL     → nvidia/llama-3.1-nemotron-70b-instruct
    """

    NAME = "nvidia"
    DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
    DEFAULT_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"

    def __init__(self):
        self._ready: Optional[bool] = None
        self._client = None

    def _get_client(self):
        """Obtiene o crea el cliente OpenAI apuntando a Nvidia NIM."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=os.getenv("NVIDIA_API_KEY", ""),
                    base_url=os.getenv("NVIDIA_BASE_URL", self.DEFAULT_BASE_URL),
                )
            except ImportError:
                raise RuntimeError(
                    "La librería 'openai' no está instalada. "
                    "Agregar 'openai' a requirements.txt para usar Nvidia NIM."
                )
        return self._client

    def _check_ready(self) -> bool:
        if self._ready is None:
            self._ready = bool(os.getenv("NVIDIA_API_KEY", "").strip())
        return self._ready

    async def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: str = "",
        max_tokens: int = 2048,
        tools: Optional[List[dict]] = None,
    ) -> LLMResponse:
        """Llama al modelo Nvidia NIM de forma asíncrona."""
        if not self._check_ready():
            raise RuntimeError("NVIDIA_API_KEY no configurado.")

        client = self._get_client()
        model = os.getenv("NVIDIA_MODEL", self.DEFAULT_MODEL)

        # Construir lista de mensajes en formato OpenAI
        oai_messages = []
        if system_prompt:
            oai_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            oai_msg = {"role": msg.role, "content": msg.content}
            if msg.tool_call_id:
                oai_msg["tool_call_id"] = msg.tool_call_id
            if msg.name:
                oai_msg["name"] = msg.name
            oai_messages.append(oai_msg)

        # Construir tools en formato OpenAI si hay
        oai_tools = None
        if tools:
            oai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.get("name", ""),
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {}),
                    },
                }
                for t in tools
            ]

        kwargs = {
            "model": model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
        }
        if oai_tools:
            kwargs["tools"] = oai_tools
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)

        choice = response.choices[0] if response.choices else None
        text = ""
        tool_calls = []

        if choice:
            msg_out = choice.message
            text = msg_out.content or ""
            if msg_out.tool_calls:
                for tc in msg_out.tool_calls:
                    import json
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments or "{}"),
                    })

        return LLMResponse(
            text=text.strip(),
            provider=self.NAME,
            tool_calls=tool_calls,
            raw=response,
        )


# ---------------------------------------------------------------------------
# Orquestador con fallback
# ---------------------------------------------------------------------------

class LLMProvider:
    """
    Orquestador que intenta con Gemini primero; si falla, usa Nvidia NIM.
    El orden puede configurarse con la variable de entorno LLM_PRIMARY.
      LLM_PRIMARY=gemini  → Gemini primero, Nvidia de fallback
      LLM_PRIMARY=nvidia  → Nvidia primero, Gemini de fallback
    """

    def __init__(self):
        self._gemini = GeminiProvider()
        self._nvidia = NvidiaProvider()
        primary = os.getenv("LLM_PRIMARY", "gemini").lower()
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS")
        if gemini_key:
            primary = "gemini"
        if primary == "nvidia":
            self._providers = [self._nvidia, self._gemini]
        else:
            self._providers = [self._gemini, self._nvidia]

    async def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: str = "",
        max_tokens: int = 2048,
        tools: Optional[List[dict]] = None,
    ) -> LLMResponse:
        """
        Intenta generar respuesta con el proveedor primario.
        Si falla, intenta con el siguiente proveedor disponible.
        """
        last_error: Optional[Exception] = None

        for provider in self._providers:
            # Saltar proveedores no configurados
            if hasattr(provider, "_check_ready") and not provider._check_ready():
                logger.debug("Proveedor %s no disponible, saltando.", provider.NAME)
                continue
            try:
                logger.info("Llamando a proveedor LLM: %s", provider.NAME)
                response = await provider.generate(
                    messages=messages,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    tools=tools,
                )
                return response
            except Exception as exc:
                if provider.NAME == "gemini":
                    logger.error(
                        "Gemini falló antes del fallback. Causa exacta: %s",
                        exc,
                        exc_info=True,
                    )
                logger.warning(
                    "Proveedor %s falló: %s. Intentando fallback...",
                    provider.NAME,
                    exc,
                )
                last_error = exc

        raise RuntimeError(
            f"Todos los proveedores LLM fallaron. Último error: {last_error}"
        )


# Instancia singleton reutilizable
_llm_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Retorna la instancia singleton del proveedor LLM."""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = LLMProvider()
    return _llm_provider
