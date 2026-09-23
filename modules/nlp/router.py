"""Deterministic intent router.

Compatibilidad: este archivo funciona como entrypoint público.
Internamente delega a `modules.nlp.router.main`.

Importante:
- Firestore writes happen only in deterministic router/actions.
- Gemini fallback is used only when no deterministic parser matches.
"""

from modules.nlp.router.main import procesar_intencion_natural

__all__ = ["procesar_intencion_natural"]
