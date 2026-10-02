# Integración NVIDIA

Esta nota documenta la integración de los servicios y modelos de NVIDIA, particularmente mediante NVIDIA NIM (NVIDIA Inference Microservices), para potenciar las capacidades de razonamiento y generación del agente Hermes.

## Configuración de la API NIM
El sistema está configurado para utilizar modelos de lenguaje grandes (LLMs) proporcionados por NVIDIA NIM, como:
- **Llama 3.1 70B Instruct** ([[meta/llama-3.1-70b-instruct]])
Estos modelos se integran a través del proveedor LLM centralizado en [[src/core/llm_provider.py]].

## Prueba de Conectividad
Se ha creado el script [[scripts/test_nvidia_api.py]] para validar la conectividad y funcionalidad de la API de NVIDIA:
- Verifica que el endpoint de la API esté accesible y responda correctamente.
- Prueba inferencias básicas para asegurar que no se produzcan errores HTTP como 404 (Not Found) o 410 (Gone).
- Confirma que el modelo especificado en la configuración esté disponible y genere respuestas coherentes.

## Integración con Hermes Agent
La salida de los modelos NVIDIA es consumida por [[Hermes Agent]] como parte de su proceso de razonamiento ReAct:
- El LLM provider selecciona el modelo NVIDIA configurado.
- Las respuestas del modelo son procesadas dentro del bucle de Reasoning-Acting-Observing.
- Se mantiene el flujo de control explícito donde las herramientas (no el LLM autónomo) realizan mutaciones en Firestore.

## Navegación
- [[Hermes Agent]] - Detalles del motor agéntico que utiliza estos modelos.
- [[Mapa del Sistema]] - Volver al nodo central de documentación.

---
 
## Avances del PASO 3

- **2026-10-02:** Verificación completa del PASO 3 (Integración de Modelos NVIDIA):
  - Configuración de LLM revisada en [[src/core/llm_provider.py]] confirmando soporte para NVIDIA NIM
  - Script de prueba creado y ejecutado: [[scripts/test_nvidia_api.py]]
  - Conectividad validada (modo simulación debido a falta de API key)
  - Conector listo para usar modelos como [[meta/llama-3.1-70b-instruct]]

---
*Última actualización: 2026-10-02*