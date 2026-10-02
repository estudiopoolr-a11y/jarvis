# Hermes Agent

Hermes es el motor agéntico de JARVIS, diseñado para actuar como el cerebro orquestador que razona y ejecuta acciones basadas en el contexto del usuario.

## Motor de Razonamiento
Implementa el patrón **ReAct (Reason → Act → Observe)** en [[src/agent/hermes_engine.py]], permitiendo que el agente:
1. Analice la solicitud del usuario.
2. Decida qué herramienta invocar.
3. Observe el resultado y refine su respuesta o reintente la acción en caso de error (auto-corrección).

## Gestión de Habilidades (Skills)
El agente posee un sistema de auto-mejora y personalización a través de la función `_cargar_skills` en [[src/agent/hermes_engine.py]]:
- **Carga Dinámica**: Lee preferencias, reglas y habilidades guardadas en la colección `skills` de [[Base de Datos Firestore]].
- **Contexto Adaptativo**: Estas habilidades se inyectan directamente en el *system prompt* del LLM, permitiendo que JARVIS "aprenda" nuevas reglas de comportamiento o preferencias del usuario sin necesidad de reprogramar el código.
- **Estructura de Skill**: Cada habilidad se almacena con un `tipo`, `nombre` y `contenido`.

## Navegación
- [[Base de Datos Firestore]] - Detalles sobre dónde se almacenan las skills.
- [[Mapa del Sistema]] - Volver al nodo central de documentación.

---
*Última actualización: 2026-10-02*

## Avances del PASO 2

- **2026-10-02:** Verificación completa del PASO 2 (Diagnóstico y Corrección de Skills en Hermes Agent):
  - Función `_cargar_skills` inspeccionada en [[src/agent/hermes_engine.py]]
  - Colección raíz `skills` en Firestore verificada e inicializada con skill de ejemplo
  - Confirmado que Hermes Agent puede leer y persistir nuevas skills correctamente
  - Scripts de validación creados: `scripts/check_skills.py` y `scripts/test_skills_persistence.py`