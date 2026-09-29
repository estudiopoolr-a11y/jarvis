"""Imprime el diagnóstico del almacén Firebase detectado en el código."""
import sys

sys.stdout.reconfigure(encoding="utf-8")

RESUMEN = """
DIAGNÓSTICO FIREBASE — JARVIS
=============================
Tipo detectado: Cloud Firestore (documental / colecciones).
No es Realtime Database: no hay firebase_admin.db ni referencias .child().

Inicialización:
  modules/firestore/client.py -> firebase_admin.initialize_app + firestore.client()
  Credenciales: FIREBASE_CREDENTIALS | FIREBASE_CREDENTIALS_JSON | serviceAccountKey.json

Modelo activo (Kebo), raíz users/{userId}/:
  accounts/{accountId}                         nombre, type, currency, balance, institution, bank_last4
  categories/{categoryId}                      nombre, budget, tipo, icono, color
    subcategories/{subcategoryId}              nombre, icono, color
  budgets/{YYYY-MM}/items/{budgetItemId}      category_id, category_name, amount, year, month
  transactions/{YYYY-MM}/items/{transactionId} type, amount, account_id, category_id, date, tags
  goals/{goalId}                               nombre, monto_objetivo, current_amount
    aportes/{aporteId}                         monto, fecha
  recurring/{recurringId}                      nombre, monto, frecuencia, dia, account_id
  reminders/{reminderId}                       text, day, month, year, done
  loans/{loanId}                               persona, monto_original, monto_pendiente, pagos[]
  scheduled_transactions/{id}                  scheduled_date, status
  exchange_rates/{currency}                    rate

Colecciones legacy (raíz, no anidadas):
  finanzas, presupuestos, metas, pagos_fijos, tareas, perfiles, historial_chat, recordatorios

Regla de negocio preservada:
  budgets.amount es un techo mensual. No se resta de accounts.balance.

Destino relacional:
  dataconnect/schema/schema.sql
  dataconnect/schema/schema.gql
  modules/sql/  (CRUD PostgreSQL)
"""


if __name__ == "__main__":
    print(RESUMEN.strip())
