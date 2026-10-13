#!/usr/bin/env python
"""Test interceptor response formats for financial queries."""
import os
os.environ['TELEGRAM_BOT_TOKEN'] = 'test'
os.environ['GEMINI_API_KEY'] = 'test'
os.environ['FIREBASE_DATABASE_URL'] = 'https://jarvis-be47a-default-rtdb.firebaseio.com'
os.environ['FIREBASE_CREDENTIALS'] = '{"type":"service_account","project_id":"jarvis-be47a","private_key":"test","client_email":"test@test.iam.gserviceaccount.com"}'

from modules.finance.interceptor import detectar_e_interactuar_finanzas

queries = [
    ("cuál es el presupuesto de julio", "Presupuesto julio"),
    ("cuales son mis categorias", "Categorías"),
    ("muéstrame mis gastos de agosto", "Gastos agosto"),
    ("presupuesto de septiembre", "Presupuesto septiembre"),
    ("que categories tengo", "Categories (English)"),
]

for query, desc in queries:
    try:
        result = detectar_e_interactuar_finanzas(query)
        print(f"\n{'='*60}")
        print(f"TEST: {desc}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        print(result if result else "NONE (pasó al LLM)")
    except Exception as e:
        print(f"\n❌ ERROR {desc}: {e}")
