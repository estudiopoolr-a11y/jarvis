# Plan de Mejora: Análisis Financiero + Parsers de Consulta

## Diagnóstico (17 Sep 2026)

La conversación con TtvMRamos12 mostró cuatro comandos que el parser determinístico **no entendió** y cayeron a Gemini, que:

| Comando | Lo que esperaba el usuario | Lo que hizo Gemini |
|---|---|---|
| `q categorias hay?` / `pero en total de todas las bases` | Listar categorías Firestore + cuentas + presupuestos | Listó **presupuestos del mes** y regañó |
| `ya he gastado todo mi balance en esos presupuestos` + `deja lo q sobra` | Confirmar que el remanente queda libre | “excedente $56.992”, “analice los datos” |
| `ajustar mi balance a los presupuestos del mes de septiembre` | Explicar que presupuestos son techos, no restan | Se disparó el parser “ver presupuestos” |
| `dame una analisis financiero` | Informe determinístico del mes | Mezcló $505k (1 mes) con $3.3M (histórico) |

### Problema raíz

1. **Faltan parsers**: categorías, análisis, sobrante, ajustar.
2. **Contexto Gemini mezcla periodos**: inyecta `Balance=$562k` (histórico) junto a `Pres: {Casa, Mamá, Deudas}` (septiembre), y Gemini los resta como si fueran el mismo concepto.
3. **El parser `ver presupuestos` es muy goloso**: se dispara con cualquier texto que contenga `presupuesto` y número, incluso si la intención es otra.
4. **Tono condescendiente**: `Frío, analítico, directo` + solo lectura produce respuestas como `Analice los datos antes de emitir conclusiones erróneas`.

### Tres métricas distintas (NUNCA mezclar)

| Concepto | Cómo obtenerlo | Qué significa |
|---|---|---|
| Liquidez en cuentas | `listar_cuentas → sum(balance)` | Dinero real disponible |
| Neto del mes | `obtener_balance_financiero(mes=YYYY-MM)` | Ingresos − gastos del periodo |
| Neto histórico | `obtener_balance_financiero()` (sin mes) | Neto acumulado de todos los meses |
| Presupuestos del mes | `obtener_presupuestos_v2(mes=YYYY-MM)` | Techos de gasto y cuánto se ha gastado de cada uno |

**Regla**: un presupuesto mensual solo se compara con los gastos del mismo mes.

## Cambios

### 1. Parsers determinísticos en `modules/ai.py`

Insertar **antes** del bloque `4b. VER PRESUPUESTOS` (línea ~1633), ya que ese bloque se come cualquier `presupuesto`.

| Intención | Patrón | Respuesta |
|---|---|---|
| Listar categorías | `(categorias\|categorías\|categoria\|categoría).*(hay\|cuántas\|cuáles\|cuales\|listar\|ver\|mostrar\|todas)` | `listar_categorias()` + presupuestos del mes + cuentas. No Gemini. |
| Análisis del mes | `(analisis\|análisis\|analiza\|analice\|resumen\|reporte) (financiero\|mensual\|del mes\|de septiembre\|completo)` | Informe determinístico: liquidez, neto del mes, cada presupuesto vs gastado, gastos sin categoría, excedente del mes. |
| Sobrante libre | `(deja\|dejar\|sobra\|sobrante\|excedente\|no (asignes\|uses\|gastes))` | `¿Quieres dejar el remanente libre (no crear presupuesto con él)?` → sí: mensaje de confirmación; no: sugerir comando |
| Ajustar balance | `ajustar.*balance.*presupuesto` | Explicación corta + sugerencia |
| Ver presupuestos | Requiere palabra de consulta (`dame\|ver\|mostrar\|hay\|cuáles\|cuales\|lista`) | Solo entonces dispara el listado |

### 2. Contexto financiero etiquetado (`modules/db.py:obtener_contexto_financiero`)

Cambiar de:
```
[JARVIS] Balance=$561,992 Ing=$3,862,707 Gas=$3,300,716 | Pres:{Casa:150k, Mamá:150k, Deudas:205k} | Mov:[...]
```

a:
```
[JARVIS] LIQUIDEZ_CUENTAS=$X | MES_ACTUAL(2026-09): Ing=$Y Gas=$Z Neto=$W | PRESUPUESTOS_MES:{Casa:150k(gastado:0), Mamá:150k(gastado:0), Deudas:205k(gastado:140k)} | HISTORICO: Ing=$A Gas=$B Neto=$C | MOV_ACTUAL:[D:35k@Gym, D:140k@Deudas, D:212k@Moto]
```

Nunca un solo `Balance=$` sin etiqueta de periodo.

### 3. Tono del SYSTEM_INSTRUCTION

Cambiar de `Frío, analítico, directo` a `Directo pero amable. Responde con datos reales, no contradigas al usuario. Si el usuario dice algo incorrecto, preséntale los datos sin juzgar. No mezcles periodos distintos.`

### 4. Tests

Añadir a `tests/test_parsers.py`:

- `test_listar_categorias`: `q categorias hay` → True
- `test_analisis_financiero`: `dame una analisis financiero` → True (typo)
- `test_deja_lo_que_sobra`: `deja lo que sobra` → True
- `test_ajustar_balance`: `ajustar mi balance a los presupuestos de septiembre` → True
- `test_ver_presupuesto_no_se_dispara_en_ajustar`: `ajustar mi balance a los presupuestos` → `_parse_ver_presupuesto()` retorna None

### 5. TODO.md

Marcar tareas viejas como completadas y añadir este sprint.

## No hacer

- ❌ No borrar presupuestos de Casa/Mamá/Deudas (están correctos)
- ❌ No mutar saldos de cuentas sin confirmación explícita
- ❌ No llamar a Gemini para análisis mensuales (debe ser determinístico)
- ❌ No restar techos presupuestarios del neto histórico (son periodos distintos)

## Verification

```bash
py -3 -m unittest tests.test_parsers -v
```

Confirmar que `obtener_contexto_financiero` devuelva etiquetas `LIQUIDEZ_CUENTAS`, `MES_ACTUAL`, `HISTORICO`.