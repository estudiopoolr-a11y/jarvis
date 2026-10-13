#!/usr/bin/env python
import os
os.environ['TELEGRAM_BOT_TOKEN'] = '1234567890:ABCdefGHIjklMNOpqrstUVWxyz'
os.environ['GEMINI_API_KEY'] = 'test'
os.environ['FIREBASE_DATABASE_URL'] = 'https://jarvis-be47a-default-rtdb.firebaseio.com'
os.environ['FIREBASE_CREDENTIALS'] = '{"type":"service_account","project_id":"jarvis-be47a","private_key":"-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDxQ\\n-----END PRIVATE KEY-----\\n","client_email":"test@test.iam.gserviceaccount.com","client_id":"123"}'

import asyncio
from modules.finance.interceptor import detectar_e_interactuar_finanzas

async def test():
    queries = [
        'cuál es el presupuesto de julio',
        'cuales son mis categorias',
        'que categorias tengo',
        'muéstrame mis gastos de agosto',
        'hola, que tal'
    ]
    for q in queries:
        try:
            r = detectar_e_interactuar_finanzas(q)
            print(f"\n--- Query: {q} ---")
            print(r[:500] if r else "NONE (pasó al LLM)")
        except Exception as e:
            print(f"\n--- Query: {q} --- ERROR: {e}")

asyncio.run(test())