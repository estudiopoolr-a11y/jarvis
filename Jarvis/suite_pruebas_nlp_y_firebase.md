# Suite de Pruebas NLP y Firebase

## Descripción
Batería de pruebas automatizadas para validar el análisis NLP dinámico con Gemini y las consultas en tiempo real hacia Firebase.

## Tests Incluidos

### test_analisis_intencion_presupuesto
Prueba unitaria para el análisis de intención de presupuesto.
- Ejecuta `analizar_intencion_mensaje("cual es el presupuesto de julio")`
- Valida que el resultado sea un diccionario estructurado con la clave `intencion`

### test_ejecucion_nlp_dinamica
Prueba unitaria para la ejecución de intenciones NLP.
- Ejecuta el manejador NLP con un diccionario de intención simulado `CONSULTAR_PRESUPUESTO`
- Valida que la respuesta sea una cadena de texto no vacía

### test_router_q_cuenta_tengo
Prueba que 'q cuenta tengo' sea manejado por el router determinista.
- Verifica que la consulta sea clasificada correctamente por el router principal

### test_router_mi_balance
Prueba que 'mi balance' sea manejado por el router determinista.
- Verifica que la consulta sea clasificada correctamente por el router principal

### test_router_presupuesto_julio
Prueba que 'presupuesto de julio' sea manejado por el router determinista.
- Verifica que la consulta sea clasificada correctamente por el router principal

## Estado de las Pruebas
- **Total de tests:** 11 (5 nuevos + 6 existentes)
- **Tests pasando:** 11/11
- **Tests fallando:** 0/11

## Archivos Modificados
- `tests/test_nlp_firebase.py` - Nueva suite de pruebas
- `modules/nlp/router/main.py` - Agregado 'q' y 'mi' a palabras clave balance/finanzas
- `modules/nlp/actions/presupuestos.py` - Agregado patrones 'q cuenta tengo' y 'q cuentas tengo'
- `app/core/organisms/finance_organism.py` - Reemplazado valores hardcoded por consultas reales a Firebase

## Comandos de Ejecución
```bash
python -m unittest discover -v tests
```

## Etiquetas
[[FastAPI]], [[Gemini API]], [[Firebase]], [[Python]], [[Testing]]