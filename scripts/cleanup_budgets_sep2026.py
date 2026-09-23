#!/usr/bin/env python3
"""Limpia presupuestos corruptos de septiembre 2026.

Usuario: 1536228767180136498
Periodo: 2026-09

Conserva (y upserta montos canónicos):
  - Casa:   $150,000
  - Mamá:   $150,000
  - Deudas: $205,000

Borra documentos claramente corruptos (Hola Yerbis, Septiembre.,
Son 205.000 No, Mamá Deudas,, frases de comando, nombres con dígitos).

Nombres cortos desconocidos que parecen categorías reales se conservan
y se reportan, no se borran.

No muta accounts, transactions ni otros meses.
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.db import (  # noqa: E402
    _cat_exacta,
    _normalizar_cat_str,
    establecer_presupuesto_mes,
    inicializar_firebase,
    _get_user_ref,
)

USUARIO_ID = "1536228767180136498"
YEAR = "2026"
MONTH = "09"
PERIOD = f"{YEAR}-{MONTH}"

KEEP = {
    "Casa": 150000,
    "Mamá": 150000,
    "Deudas": 205000,
}

GARBAGE_PREFIXES = (
    "son 205",
    "septiembre",
    "hola yerbis",
    "hola, yerbis",
    "necesito q edites",
    "necesito que edites",
    "mama deudas",
    "mamá deudas",
)

MESES = {
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
}


def _keep_canonical(name):
    """Devuelve el nombre canónico de allowlist si hay coincidencia exacta."""
    for canonical in KEEP:
        if _cat_exacta(name, canonical):
            return canonical
    return None


def _es_basura(name):
    """Detecta documentos creados por parsers viejos / frases de comando."""
    if not name or not str(name).strip():
        return True
    raw = str(name).strip()
    norm = _normalizar_cat_str(raw)
    if not norm:
        return True
    if _keep_canonical(raw):
        return False
    if any(norm.startswith(_normalizar_cat_str(p)) or _normalizar_cat_str(p) in norm
           for p in GARBAGE_PREFIXES):
        return True
    if re.search(r"\d", raw):
        return True
    if norm in MESES:
        return True
    if len(raw) > 40:
        return True
    tokens = norm.split()
    command_tokens = {
        "hola", "yerbis", "necesito", "edites", "ponle", "pones",
        "puedes", "poner", "categoria", "presupuesto", "presupuestos",
    }
    if sum(1 for t in tokens if t in command_tokens) >= 2:
        return True
    return False


def _fmt_amount(amt):
    try:
        return f"${float(amt):,.0f}"
    except (TypeError, ValueError):
        return f"${amt}"


def main():
    db = inicializar_firebase()
    if not db:
        print("❌ Firebase no inicializada. Revisa serviceAccountKey.json o FIREBASE_CREDENTIALS.")
        sys.exit(1)

    _, uref = _get_user_ref(USUARIO_ID)
    if not uref:
        print(f"❌ Usuario {USUARIO_ID} no encontrado.")
        sys.exit(1)

    items_ref = uref.collection("budgets").document(PERIOD).collection("items")
    docs = list(items_ref.stream())

    print(f"=== Limpieza presupuestos {PERIOD} para {USUARIO_ID} ===")
    print(f"\nInventario inicial: {len(docs)} documento(s)")
    for doc in docs:
        data = doc.to_dict() or {}
        print(f"  • {doc.id}: '{data.get('category_name', '')}' ({_fmt_amount(data.get('amount', 0))})")

    keep_docs = {canonical: [] for canonical in KEEP}
    to_delete = []
    unknown = []

    for doc in docs:
        data = doc.to_dict() or {}
        name = data.get("category_name", "")
        canonical = _keep_canonical(name)
        if canonical:
            keep_docs[canonical].append(doc)
            continue
        if _es_basura(name):
            to_delete.append((doc, name, data.get("amount", 0)))
        else:
            unknown.append((doc, name, data.get("amount", 0)))

    print("\n--- Acciones ---")

    deleted_count = 0
    for doc, name, amt in to_delete:
        print(f"  🗑️  Borrar basura: '{name}' ({_fmt_amount(amt)}) [{doc.id}]")
        doc.reference.delete()
        deleted_count += 1

    extra_deleted = 0
    for canonical, matches in keep_docs.items():
        if len(matches) <= 1:
            continue
        # Conservar el de nombre más corto/limpio; borrar duplicados.
        matches_sorted = sorted(
            matches,
            key=lambda d: len(str((d.to_dict() or {}).get("category_name", ""))),
        )
        keep_one, extras = matches_sorted[0], matches_sorted[1:]
        keep_name = (keep_one.to_dict() or {}).get("category_name", canonical)
        print(f"  ♻️  Duplicados de {canonical}: conservar '{keep_name}' [{keep_one.id}]")
        for extra in extras:
            extra_name = (extra.to_dict() or {}).get("category_name", "")
            extra_amt = (extra.to_dict() or {}).get("amount", 0)
            print(f"     🗑️  Duplicado: '{extra_name}' ({_fmt_amount(extra_amt)}) [{extra.id}]")
            extra.reference.delete()
            extra_deleted += 1

    for doc, name, amt in unknown:
        print(f"  ⚠️  Conservar desconocido (no parece basura): '{name}' ({_fmt_amount(amt)}) [{doc.id}]")

    print("\n--- Upsert montos canónicos ---")
    for canonical, amount in KEEP.items():
        ok = establecer_presupuesto_mes(USUARIO_ID, canonical, amount, YEAR, MONTH)
        estado = "OK" if ok else "FALLÓ"
        print(f"  {'✅' if ok else '❌'} {canonical} = {_fmt_amount(amount)} ({estado})")

    print("\n--- Categorías basura ---")
    cats_deleted = 0
    cats_ref = uref.collection("categories")
    for cdoc in cats_ref.stream():
        cd = cdoc.to_dict() or {}
        cname = cd.get("nombre", "")
        if _keep_canonical(cname):
            continue
        if _es_basura(cname):
            print(f"  🗑️  Categoría: '{cname}' [{cdoc.id}]")
            cdoc.reference.delete()
            cats_deleted += 1
    if cats_deleted == 0:
        print("  (ninguna)")

    print(f"\n--- Estado final de presupuestos {PERIOD} ---")
    final_items = list(items_ref.stream())
    found = {}
    for fdoc in final_items:
        fd = fdoc.to_dict() or {}
        fname = fd.get("category_name", "")
        famt = fd.get("amount", 0)
        print(f"  • {fname}: {_fmt_amount(famt)} [{fdoc.id}]")
        canonical = _keep_canonical(fname)
        if canonical:
            found[canonical] = float(famt or 0)

    print("\n--- Verificación ---")
    ok_all = True
    for canonical, amount in KEEP.items():
        actual = found.get(canonical)
        if actual is None:
            print(f"  ❌ Falta {canonical}")
            ok_all = False
        elif abs(actual - amount) > 0.01:
            print(f"  ❌ {canonical}: esperado {amount:.0f}, actual {actual:.0f}")
            ok_all = False
        else:
            print(f"  ✅ {canonical}: {_fmt_amount(actual)}")

    extras_final = [
        (fdoc.to_dict() or {}).get("category_name", "")
        for fdoc in final_items
        if not _keep_canonical((fdoc.to_dict() or {}).get("category_name", ""))
    ]
    garbage_left = [n for n in extras_final if _es_basura(n)]
    if garbage_left:
        print(f"  ❌ Basura restante: {garbage_left}")
        ok_all = False
    else:
        print("  ✅ Sin documentos corruptos")

    print(
        f"\nResumen: borrados={deleted_count + extra_deleted} "
        f"(items basura={deleted_count}, duplicados={extra_deleted}), "
        f"categorías borradas={cats_deleted}, "
        f"desconocidos conservados={len(unknown)}"
    )
    if not ok_all:
        print("❌ Limpieza incompleta.")
        sys.exit(1)
    print("✅ Limpieza completada.")


if __name__ == "__main__":
    main()
