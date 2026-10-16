# Motor de Asesoría Financiera Inteligente

## Propósito

`[[modules/finance/advisor.py]]` prepara una propuesta presupuestal informativa
cuando Telegram recibe preguntas como “¿qué presupuesto debería asignar en
octubre?” o “¿en qué debería ahorrar?”. La intención se reconoce en
`[[modules/finance/interceptor.py]]` antes de que la consulta llegue a Gemini o
NVIDIA, evitando responder con el resumen vacío del mes destino o con cifras
generadas por un modelo.

## Fuente y cálculo

- Fuente única: agregados reales de [[Firebase]]/Firestore a través de
  `[[modules/finance/dashboard.py]]`.
- El asesor inspecciona meses anteriores al mes solicitado, hasta encontrar
  cuatro meses con ingresos o gastos registrados. Los meses vacíos se omiten.
- El ingreso proyectado es el promedio de meses históricos que registran
  ingresos positivos.
- El tope sugerido de cada categoría es su gasto histórico agregado dividido
  entre el número de meses activos utilizados. Las categorías sin gasto en un
  mes activo cuentan como cero en ese promedio.
- El excedente estimado para ahorro/inversión es el máximo entre cero y la
  diferencia del ingreso proyectado y la suma de los topes sugeridos.
- Si no existe historial activo, el asesor lo informa y no inventa ingresos,
  gastos ni topes.

La propuesta incluye los meses usados para que el origen del promedio sea
auditable. Los importes son estimaciones, no una garantía de ingresos futuros.
La recomendación de ahorro/inversión es general, no personalizada; el módulo no
ejecuta inversiones ni escribe un presupuesto automáticamente. El usuario debe
confirmar antes de guardar una propuesta.

## Persistencia

El subsistema operativo de finanzas consulta [[Firebase]]/Firestore. No existe
una llamada activa a Notion en el asesor; la nota solicitada
`esquema_prestamos_y_topes_notion.md` no está presente en esta bóveda. El
esquema de presupuestos utilizado por el dashboard es
`budgets/{YYYY-MM}/items`, y los gastos se agregan desde
`transactions/{YYYY-MM}/items`.

## Pruebas

`[[tests/test_finance_advisor.py]]` comprueba el promedio con meses activos,
el salto de meses vacíos, la respuesta sin historial, la detección del mensaje
de Telegram y el respeto del año solicitado. Ejecutar:

```powershell
python -m unittest tests.test_finance_advisor -v
```

Tags: [[Finanzas]] [[Python]] [[IA]] [[FastAPI]] [[Telegram]] [[Firebase]]
