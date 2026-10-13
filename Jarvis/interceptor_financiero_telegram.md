# Interceptor Financiero en Telegram

## Resumen
Se implementó un interceptor que detecta consultas financieras antes de que lleguen al LLM (Gemini/NVIDIA NIM), evitando alucinaciones de datos.

## Fecha
2026-08-15

## Problema Identificado
Cuando el bot de Telegram recibía consultas como *"cuál es tu presupuesto de julio"*, el LLM alucinaba valores porque no tenía conexión directa a Firestore en el flujo de texto plano.

## Solución

### 1. Módulo Interceptor (`modules/finance/interceptor.py`)
- Detección por palabras clave: presupuesto, gasto, balance, ingreso, categorías, etc.
- Normalización de texto (acentos) para coincidencia robusta
- Consulta directa a Firestore usando `obtener_resumen_dashboard()`
- Respuesta formateada con datos reales sin intervención del LLM

### 2. Integración en Webhook (`app/routes/telegram.py`)
- **PASO 0**: Interceptor financiero ejecutado ANTES de cualquier LLM
- Si se detecta intención financiera, se responde con datos reales de Firestore
- Si no, continúa con el flujo normal (Gemini/NVIDIA NIM)

### 3. Corrección Crítica Encontrada
- `detectar_e_interactuar_finanzas()` es una función **síncrona** (no async)
- Se debe llamar directamente, NO con `await`
- El `resolver_llamada_segura()` funciona para ambos casos (sync y async)

## Palabras Clave Detectadas
```python
_KEYWORDS = [
    "presupuesto", "presupuestos",
    "gasto", "gastos", "gasté", "gaste", "gastado", "gastar",
    "balance", "saldo",
    "ingreso", "ingresos", "ingrese", "ingresar",
    "cuánto tengo", "cuanto tengo",
    "debo", "deuda", "deudas",
    "prestamo", "prestamos",
    "dinero", "plata",
    "cuánto cuesta", "cuanto cuesta", "precio", "costo",
    "cobrar", "cobro", "cobré", "cobre",
    "pagar", "pago", "pagué", "pague",
    "categoria", "categorias", "category", "categories",
]
```

## Datos Reales de Ejemplo (Julio 2026)
- Ingresos: $936,455 COP
- Gastos: $1,094,776 COP
- Presupuesto: $1,260,000 COP
- Uso: 86.9%

## Pruebas
```bash
python -m unittest discover -v tests  # 30/30 OK
curl.exe -s "https://jarvis-two-pi-13.vercel.app/api/widget/dashboard?usuario_id=default&mes=2026-07"
```

## Enlaces
- [[Firebase]] | [[Finanzas]] | [[Python]] | [[FastAPI]] | [[Telegram]]

## Estado
✅ Implementado y desplegado en Vercel (jarvis-two-pi-13.vercel.app)
