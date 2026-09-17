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
