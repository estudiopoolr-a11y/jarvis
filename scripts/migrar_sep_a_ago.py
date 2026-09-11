#!/usr/bin/env python3
"""migrar_sep_a_ago.py

Para el usuario maestro 1536228767180136498:
- Copia TODOS los gastos (transactions/2026-09/items) a transactions/2026-08/items
  ajustando el campo `date` de 2026-09 a 2026-08.
- Copia los presupuestos (budgets/2026-09/items) a budgets/2026-08/items.
- Limpia completamente septiembre 2026:
  - borra TODOS los items de transactions/2026-09/items (incluye ingresos)
  - borra TODOS los items de budgets/2026-09/items

Se asume que agosto 2026 ya tiene el ingreso correcto (type=income) o si no, igualmente
se mantiene (no se copia income desde septiembre porque el usuario pidió ingresos de septiembre = 0).

Idempotente-ish: al inicio borra gastos y presupuestos existentes en agosto para evitar duplicados.
"""

import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules import database as dbmod

def main():
    db = dbmod.inicializar_firebase()
    if not db:
        print('❌ Firebase no inicializada')
        sys.exit(1)

    uid = '1536228767180136498'
    u = db.collection('users').document(uid)

    # Meses
    tx_src_month = '2026-09'
    tx_dst_month = '2026-08'

    src_tx_items = u.collection('transactions').document(tx_src_month).collection('items')
    dst_tx_items = u.collection('transactions').document(tx_dst_month).collection('items')

    src_bg_items = u.collection('budgets').document(tx_src_month).collection('items')
    dst_bg_items = u.collection('budgets').document(tx_dst_month).collection('items')

    print(f'=== Migrar SEP->{tx_dst_month} para {uid} ===')

    # 1) Limpiar agosto: borrar gastos existentes en agosto, y presupuestos existentes en agosto
    #    (si no hay, simplemente no borrará nada)
    print('1) Limpieza previa en agosto (gastos + presupuestos)...')

    aug_tx_docs = list(dst_tx_items.stream())
    aug_expense = [d for d in aug_tx_docs if (d.to_dict() or {}).get('type') == 'expense']
    for d in aug_expense:
        d.reference.delete()

    for d in list(dst_bg_items.stream()):
        d.reference.delete()

    print(f'   - Gastos agosto borrados: {len(aug_expense)}')
    print('   - Presupuestos agosto borrados: OK')

    # 2) Copiar gastos de septiembre a agosto
    print('2) Copiando gastos de septiembre a agosto...')
    sep_tx_docs = list(src_tx_items.stream())

    moved = 0
    for d in sep_tx_docs:
        data = d.to_dict() or {}
        if data.get('type') != 'expense':
            continue

        # ajustar date
        if isinstance(data.get('date'), str):
            data['date'] = data['date'].replace('2026-09', '2026-08', 1)

        # set con doc id nuevo para evitar choque de IDs
        new_doc = dst_tx_items.document()
        data['moved_from'] = tx_src_month
        new_doc.set(data)
        moved += 1

    print(f'   - Gastos movidos: {moved}')

    # 3) Copiar presupuestos de septiembre a agosto
    print('3) Copiando presupuestos de septiembre a agosto...')
    sep_bg_docs = list(src_bg_items.stream())
    bg_moved = 0
    for d in sep_bg_docs:
        data = d.to_dict() or {}
        new_doc = dst_bg_items.document()
        data['moved_from'] = tx_src_month
        new_doc.set(data)
        bg_moved += 1

    print(f'   - Presupuestos movidos: {bg_moved}')

    # 4) Borrar septiembre completamente (transactions items + budgets items)
    print('4) Borrando septiembre 2026 (tx items + budgets items)...')
    sep_tx_count = 0
    for d in list(src_tx_items.stream()):
        d.reference.delete()
        sep_tx_count += 1

    sep_bg_count = 0
    for d in list(src_bg_items.stream()):
        d.reference.delete()
        sep_bg_count += 1

    print(f'   - Sep tx items borrados: {sep_tx_count}')
    print(f'   - Sep budgets items borrados: {sep_bg_count}')

    print('\n✅ Migración completa.')

if __name__ == '__main__':
    main()
