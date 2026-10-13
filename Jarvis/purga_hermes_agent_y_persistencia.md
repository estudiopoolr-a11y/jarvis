# Purga del agente legado y persistencia serverless

## Runtime retirado

Se eliminó el runtime legado que estaba ubicado en `src/agent/` y su proveedor
dedicado en `src/core/llm_provider.py`. La aplicación activa no importaba ese
motor. Dos consumidores financieros sí reutilizaban su normalizador de texto;
esa utilidad se trasladó a `modules/nlp/text.py` para mantener el matching de
nombres de cuentas sin conservar dependencias del agente.

El webhook activo permanece en [[app/routes/telegram.py]]: prioriza el router
determinístico y usa `analizar_solicitud_consciente` para las solicitudes que
el router no reconoce. [[Gemini API]] interpreta las consultas; las acciones
de negocio siguen implementadas por los módulos del backend.

## Persistencia en Vercel

[[Firebase]]/Firestore es la persistencia usada por los módulos financieros,
de recordatorios y objetivos mediante el cliente compartido
`modules/firestore/client.py`. Sus credenciales se proporcionan mediante
variables protegidas de entorno; no se requiere almacenamiento local
persistente en las instancias Serverless.

No se encontró una integración activa con Notion en los módulos de runtime.
Firestore conserva los datos operacionales que consume el backend; Notion no
se considera una interfaz humana integrada ni una dependencia de despliegue.
No se asume una ventaja cuantitativa de latencia frente a servicios alternos.

La función `normalizar_texto` se cubre con una prueba unitaria y el cambio
completo se valida con `python -m unittest discover -v tests`.

Etiquetas: [[FastAPI]] [[Vercel]] [[Firebase]] [[Gemini API]] [[Python]]
