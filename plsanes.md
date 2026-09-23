# Plan de Corrección Integral de Presupuestos en JARVIS

A partir de la transcripción enviada, se identificó un fallo en cadena en el flujo de presupuestos:
1. **Alucinación de Gemini**: El usuario pidió eliminar presupuestos con oraciones naturales largas y múltiples elementos (`necesito q elimines los presupuestps de X y el de Y y el de Z`). El parser determinístico falló por typos/subjuntivo/múltiples categorías, cayendo a Gemini en `pensar_respuesta()`. Como Gemini no tiene herramientas para mutar Firestore en texto plano, respondió alucinando que la base de datos había sido depurada.
2. **Falso positivo de creación de presupuesto**: Al pedir renombrar y cambiar monto (`el presupuesto de septiembre renómbralo y ponle q sea de deudas y son 205.000 no 105.000`), el parser de renombrar falló (no reconocía `renómbralo` ni estructuras con `ponle q sea`), y el parser múltiple detectó `presupuesto` + montos, capturando erróneamente `"Son 205.000 No"` como categoría con valor `$105,000`.
3. **Persistencia de basura en Firestore**: Los presupuestos corruptos previos (`Septiembre.`, `Hola, Yerbis. Yerbis, Puedes Poner`, `Mamá Deudas,`, etc.) seguían existiendo en `users/1536228767180136498/budgets/2026-09/items/`.
4. **Coincidencia difusa ambigua en `_coincidir_categoria`**: `b in d` en `modules/db.py` puede causar que buscar `Mamá` coincida con `Mamá Deudas,` antes que con `Mamá` si no se prioriza la coincidencia exacta.

---

## User Review Required

> [!IMPORTANT]
> Se limpiará directamente la base de datos de Septiembre 2026 para el usuario `1536228767180136498`, dejando únicamente:
> - **Casa**: $150,000
> - **Mamá**: $150,000
> - **Deudas**: $205,000
> Los documentos huérfanos/corruptos (`Septiembre.`, `Son 205.000 No`, `Mamá Deudas,`, etc.) serán eliminados.

---

## Proposed Changes

### Base de Datos Firestore (Acción Inmediata)
- Ejecutar script de mantenimiento para depurar la colección `users/1536228767180136498/budgets/2026-09/items/`.
- Dejar exactamente:
  - `Mamá`: $150,000
  - `Deudas`: $205,000

---

### [modules/db.py](file:///c:/Users/DEEL/OneDrive/Desktop/Projects/jarvis/modules/db.py)

#### [MODIFY] [db.py](file:///c:/Users/DEEL/OneDrive/Desktop/Projects/jarvis/modules/db.py)
- **Mejorar `_coincidir_categoria` y búsquedas en `eliminar_presupuesto_mes`, `modificar_presupuesto_mes`, `renombrar_presupuesto_mes`**:
  - Implementar estrategia de 2 pasadas: primero buscar coincidencia **exacta** normalizada (`d == b`).
  - Solo si no existe coincidencia exacta, recurrir a coincidencia parcial (`b in d or d in b`).
  - Evitar que al intentar borrar o modificar `Mamá` se afecte `Mamá Deudas` o viceversa.

---

### [modules/ai.py](file:///c:/Users/DEEL/OneDrive/Desktop/Projects/jarvis/modules/ai.py)

#### [MODIFY] [ai.py](file:///c:/Users/DEEL/OneDrive/Desktop/Projects/jarvis/modules/ai.py)
1. **Mejorar `_parse_borrar_presupuesto`**:
   - Soportar modo subjuntivo y formas coloquiales: `elimines`, `borres`, `quites`, `remuevas`, `necesito que elimines/borres`.
   - Tolerancia a typos como `presupuestps`, `presupeusto`, etc.
   - Soportar **múltiples categorías a eliminar en un solo mensaje** (separadas por `y`, `y el de`, `,`, `el de`).
   - Si se detectan múltiples categorías, retornar lista de categorías a eliminar.
2. **Mejorar `_parse_renombrar_presupuesto`**:
   - Reconocer verbos enclíticos y variaciones: `renómbralo`, `renombralo`, `cámbialo`, `cambiale el nombre a`, `ponle que sea (de)`.
   - Permitir estructura invertida: `el presupuesto de X renómbralo a Y / ponle que sea de Y`.
   - Soportar **actualización simultánea de monto**: Si el comando incluye `y ponle [monto]` o `y son [monto] no [monto_antiguo]`, extraer tanto el nuevo nombre como el nuevo monto.
3. **Blindar `_parse_presupuesto_multiple` contra falsos positivos**:
   - Si el texto contiene intenciones de renombrar (`renombra`, `renómbralo`, `cámbiale el nombre`) o borrar (`borra`, `elimina`, `borres`, `elimines`), **NO** debe disparar la creación de presupuestos.
   - Limpieza y rechazo estricto de categorías candidatas que contengan dígitos (`Son 205.000 No`) o palabras como `no`, `son`, `era`, `que`, `sea`, `el`, `la`.
   - Normalizar puntuación antes de chequear `_STOP_CATEGORIA` para que `Septiembre.` o `Deudas,` coincidan y se limpien correctamente.
4. **Blindar `SYSTEM_INSTRUCTION` de Gemini**:
   - Instrucción explícita para que en respuestas de texto plano NUNCA afirme ni simule haber ejecutado modificaciones/borrados en la base de datos.
   - Si el usuario solicita mutaciones que llegaron al LLM, responder aclarando que no se pudo ejecutar la acción directamente o guiar en el formato esperado.

---

### [tests/test_parsers.py](file:///c:/Users/DEEL/OneDrive/Desktop/Projects/jarvis/tests/test_parsers.py)

#### [NEW] [test_parsers.py](file:///c:/Users/DEEL/OneDrive/Desktop/Projects/jarvis/tests/test_parsers.py)
- Pruebas automatizadas con `pytest` para:
  - Eliminación múltiple (`necesito q elimines los presupuestps de X y el de Y y el de Z`).
  - Renombrado compuesto con cambio de monto (`el presupuesto de septiembre renómbralo y ponle q sea de deudas y son 205.000 no 105.000`).
  - Renombrado simple con enclítico (`el presupuesto de septiembre renómbralo y ponle q sea de deudas`).
  - Prevención de creación errónea de presupuestos con números dentro del nombre (`Son 205.000 No`).
  - Coincidencia exacta vs substring en `_coincidir_categoria` (`Mamá` vs `Mamá Deudas`).

---

## Verification Plan

### Automated Tests
- Ejecutar `pytest tests/test_parsers.py` usando `py -3 -m pytest tests/test_parsers.py -v`.

### Database Verification
- Ejecutar script en Firestore para verificar el estado final en `users/1536228767180136498/budgets/2026-09/items/`:
  - Solo deben existir `Mamá: $150,000` y `Deudas: $205,000`.


 Plan: Mejorar el análisis financiero de JARVIS

 Context

 La conversación de Discord (17 Sep 2026) muestra que el CRUD de presupuestos ya funciona (Casa $150k se creó bien; Septiembre quedó en Casa/Mamá/Deudas). El fallo ahora es de comprensión financiera y de parsers de consulta, no de mutación.

 Gemini, al caer al modo conversacional, mezcló tres números distintos y contradijo al usuario:

 ┌───────────────────────────────────────────────────────────────┬─────────────────────────────┬────────────────────────────────────────────────────────────┐
 │                           Concepto                            │     Dato real (aprox.)      │                     Cómo lo usó Gemini                     │
 ├───────────────────────────────────────────────────────────────┼─────────────────────────────┼────────────────────────────────────────────────────────────┤
 │ Balance neto histórico (ingresos − gastos de todos los meses) │ $561,992                    │ Lo llamó “disponible” y “liquidez”                         │
 ├───────────────────────────────────────────────────────────────┼─────────────────────────────┼────────────────────────────────────────────────────────────┤
 │ Presupuestos de septiembre                                    │ $505,000 (Casa+Mamá+Deudas) │ Lo comparó contra el neto histórico                        │
 ├───────────────────────────────────────────────────────────────┼─────────────────────────────┼────────────────────────────────────────────────────────────┤
 │ Gastos reales de septiembre                                   │ no se inyectan bien         │ $387,700 de 3 movimientos recientes, o $3.3M del histórico │
 └───────────────────────────────────────────────────────────────┴─────────────────────────────┴────────────────────────────────────────────────────────────┘

 El usuario dijo tres cosas que el parser no entendió:

 1. q categorias hay? / pero en total de todas las bases → cayó a Gemini, que listó presupuestos del mes en vez de categorías Firestore + cuentas.
 2. ya he gastado todo mi balance en esos presupuestos + deja lo q sobra → Gemini interpretó “excedente no asignado $56,992” y regañó al usuario. El usuario quería: el resto del dinero no va a presupuesto / déjalo libre.
 3. ajustar mi balance a los presupuestos del mes de septiembre → el parser de ver presupuestos se disparó por la palabra presupuesto y solo listó el mes. No hay comando de “alinear” nada.
 4. dame una analisis financiero → Gemini usó ingresos/gastos globales ($3.8M / $3.3M) vs presupuestos de un mes ($505k) y concluyó que el 85% del gasto está “fuera de presupuesto”. Eso es un error de periodo, no un insight.

 El SYSTEM_INSTRUCTION de solo lectura (fix anterior) evitó alucinaciones de mutación, pero empujó a Gemini a un tono frío/condescendiente (Analice los datos antes de emitir conclusiones erróneas) y a rechazar comandos ambiguos en vez de interpretarlos.

 Outcome: un análisis determinístico por periodo, parsers para “categorías / sobrante / análisis”, y un Gemini que no mezcle meses ni insulte.

 ---

 Approach

 Documento de diseño en el repo (plan_mejora_analisis_financiero.md) + implementación posterior en parsers y contexto. No hay que tocar Firestore de producción ni el CRUD de presupuestos que ya quedó limpio.

 1. Separar tres métricas y nunca mezclarlas

 Hoy obtener_balance_financiero(usuario_id) sin mes suma todas las transacciones Kebo. obtener_contexto_financiero inyecta eso como Balance=$561,992 junto a Pres:{Casa, Mamá, Deudas} del mes actual. Gemini los resta.

 Cambiar obtener_contexto_financiero (modules/db.py) para inyectar bloques etiquetados:

 - Mes actual (YYYY-MM): ingresos, gastos, neto, presupuestos con límite / gastado / restante (reusar obtener_presupuestos_v2).
 - Histórico (todos los meses): ingresos, gastos, neto. Etiquetarlo como neto_historico, nunca como “disponible”.
 - Cuentas: suma de listar_cuentas como liquidez_en_cuentas (esto sí es “cuánto hay”).
 - Movimientos: últimos 3 del mes actual, no del histórico.

 Regla para Gemini y para el análisis determinístico: un presupuesto mensual solo se compara con gastos del mismo mes.

 2. Parsers determinísticos que hoy faltan (modules/ai.py)

 Insertarlos antes del bloque 4b. VER PRESUPUESTOS (línea ~1633), porque ese bloque se come cualquier mensaje que contenga la palabra presupuesto.

 ┌──────────────────────┬────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │      Intención       │            Ejemplos            │                                                    Acción                                                    │
 ├──────────────────────┼────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Listar categorías    │ q categorias hay, categorías   │ listar_categorias + presupuestos del mes + cuentas. No Gemini.                                               │
 │                      │ de todas las bases             │                                                                                                              │
 ├──────────────────────┼────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Análisis del mes     │ analisis financiero, dame un   │ Informe determinístico: liquidez cuentas, neto del mes, cada presupuesto vs gastado, gastos sin categoría de │
 │                      │ analisis                       │  presupuesto, restante libre.                                                                                │
 ├──────────────────────┼────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Sobrante / no        │ deja lo que sobra, deja lo q   │ Confirmar: no se crea presupuesto con el remanente. Mostrar liquidez − suma presupuestos del mes solo si se  │
 │ asignar              │ sobra                          │ aclara que son conceptos distintos (cuentas vs techos).                                                      │
 ├──────────────────────┼────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Ajustar balance a    │ ajustar mi balance a los       │ No mutar cuentas. Responder: “Los presupuestos son techos de gasto, no restan del balance. Septiembre tiene  │
 │ presupuestos         │ presupuestos de septiembre     │ $X asignados. Liquidez en cuentas: $Y. ¿Quieres un presupuesto ‘Libre/Otros’ con el remanente del mes?”      │
 └──────────────────────┴────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 El parser de “ver presupuestos” debe exigir consulta (dame, ver, mostrar, hay, cuáles) y no dispararse con ajustar … presupuestos.

 3. Tono y SYSTEM_INSTRUCTION

 El bloque actual de solo lectura se queda (evita alucinaciones de write). Añadir:

 - No contradecir ni regañar al usuario.
 - No restar presupuestos del neto histórico.
 - Si la frase es ambigua, ofrecer 1 interpretación + 1 comando concreto, sin sermón.
 - Si pide análisis, preferir datos del mes actual salvo que diga “todas las bases / histórico”.

 4. Documento en la carpeta del proyecto

 Crear plan_mejora_analisis_financiero.md en la raíz de JARVIS (junto a implementation_plan.md / TODO.md), con:

 - Diagnóstico de la transcripción
 - Tabla de métricas (qué es cada número)
 - Parsers a añadir
 - Cambio de contexto Gemini
 - Tests
 - Qué no hacer (no borrar Casa; no “ajustar” saldos de cuentas sin confirmación)

 Actualizar TODO.md marcando esta tarea como sprint inmediato.

 ---

 Critical files

 - plan_mejora_analisis_financiero.md — nuevo, el artefacto que pediste
 - modules/ai.py — parsers de categorías / análisis / sobrante; no interceptar “ajustar” como listado
 - modules/db.py — obtener_contexto_financiero con métricas etiquetadas por periodo
 - tests/test_parsers.py — casos de la transcripción
 - TODO.md — registrar el sprint

 Reusar (no reescribir): listar_categorias, listar_cuentas, obtener_presupuestos_v2, obtener_balance_financiero(..., mes=), obtener_resumen_presupuestos(..., mes=).

 ---

 Verification

 - Unit tests sobre los nuevos parsers con los textos reales de Discord (q categorias hay, deja lo q sobra, ajustar mi balance a los presupuestos del mes de septiembre, dame una analisis financiero).
 - Test de que obtener_contexto_financiero contiene las etiquetas mes_actual / historico / cuentas y no un único Balance=$.
 - Manual: el informe determinístico de septiembre debe comparar $505k de techos solo con gastos de 2026-09, no con $3.3M históricos.
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
