"""importador_txt.py

Parsea un reporte financiero consolidado en texto plano (el que se manda como
adjunto .txt en Discord) y lo carga en la estructura KEBO del usuario.

Formato esperado (flexible con acentos, mayúsculas y separadores de miles):

  1. INGRESOS POR MES (Año 2026):
  - Mayo: $1.061.159,03
  - Junio: $1.058.894,26
  ...

  --- AGOSTO 2026 ---
  - Alimentación: Presupuestado $150.000,00 | Gastado $150.000,00
  - Madre: Presupuestado $50.000,00 | Gastado $50.000,00
  ...

Reglas:
- Cada bloque "--- MES AÑO ---" reescribe ese mes (borra items previos).
- El ingreso del mes se toma de la sección "INGRESOS POR MES".
- Cada categoría genera 1 presupuesto (amount=Presupuestado) y, si Gastado>0,
  1 transacción expense por ese monto.
"""
import re
import unicodedata
from datetime import datetime

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "setiembre": "09", "octubre": "10",
    "noviembre": "11", "diciembre": "12",
}


def _norm(texto):
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.casefold().split())


def _parse_monto(texto):
    """Convierte '$1.061.159,03' o '97.900,00' o '806199.03' a float."""
    if texto is None:
        return 0.0
    s = str(texto).strip()
    s = s.replace("$", "").replace(" ", "")
    if not s:
        return 0.0
    # Formato español: miles con '.', decimales con ','
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # solo coma -> decimal
        s = s.replace(".", "").replace(",", ".")
    # si solo hay puntos, puede ser miles o decimal; heurística:
    # si el último grupo tras el punto tiene 2 dígitos y hay 1 punto, es decimal
    try:
        return float(s)
    except ValueError:
        s2 = re.sub(r"[^0-9.]", "", s)
        try:
            return float(s2)
        except ValueError:
            return 0.0


def parsear_reporte(texto, anio_default=None):
    """Devuelve dict {'YYYY-MM': {'income': float, 'budgets': {cat: (pres, gastado)}}}."""
    if anio_default is None:
        anio_default = datetime.now().year
    lineas = texto.splitlines()

    ingresos_por_mes = {}   # 'YYYY-MM' -> float
    meses = {}              # 'YYYY-MM' -> {'income':..., 'budgets': {cat:(p,g)}}
    mes_actual = None

    # Detectar año presente en el texto (primer 20xx)
    m_anio = re.search(r"(20\d{2})", texto)
    if m_anio:
        anio_default = int(m_anio.group(1))

    for raw in lineas:
        linea = raw.strip()
        if not linea:
            continue
        low = _norm(linea)

        # ¿Encabezado de bloque de mes?  "--- AGOSTO 2026 ---"
        m_head = re.match(r"^-+\s*([a-záéíóúñ]+)\s*(20\d{2})?\s*-+$", low)
        if m_head and m_head.group(1) in MESES:
            anio = m_head.group(2) or str(anio_default)
            mes_actual = f"{anio}-{MESES[m_head.group(1)]}"
            meses.setdefault(mes_actual, {"income": 0.0, "budgets": {}})
            continue

        # ¿Línea de ingreso mensual? "- Mayo: $1.061.159,03"
        m_ing = re.match(r"^[-•*]?\s*([a-záéíóúñ]+)\s*:\s*\$?\s*([0-9.,]+)\s*$", low)
        if m_ing and m_ing.group(1) in MESES and mes_actual is None:
            mes_key = f"{anio_default}-{MESES[m_ing.group(1)]}"
            ingresos_por_mes[mes_key] = _parse_monto(m_ing.group(2))
            continue

        # ¿Línea de categoría? "- Alimentación: Presupuestado $150.000,00 | Gastado $150.000,00"
        if mes_actual and "presupuest" in low and "gastad" in low:
            # capturar nombre y montos con el texto ORIGINAL para conservar acentos/nombre real
            m_cat = re.match(
                r"^[-•*]?\s*(.+?)\s*:\s*presupuestado\s*\$?\s*([0-9.,]+)\s*\|\s*gastado\s*\$?\s*([0-9.,]+)",
                _norm(linea),
            )
            if m_cat:
                # nombre real desde la línea original (antes de ':')
                nombre_real = raw.strip()
                nombre_real = re.sub(r"^[-•*]\s*", "", nombre_real)
                nombre_real = nombre_real.split(":", 1)[0].strip()
                pres = _parse_monto(m_cat.group(2))
                gast = _parse_monto(m_cat.group(3))
                meses[mes_actual]["budgets"][nombre_real] = (pres, gast)
            continue

    # fusionar ingresos
    for mk, inc in ingresos_por_mes.items():
        meses.setdefault(mk, {"income": 0.0, "budgets": {}})
        meses[mk]["income"] = inc

    return meses


def _cat_id_por_nombre(user_ref):
    mapa = {}
    for c in user_ref.collection("categories").stream():
        d = c.to_dict() or {}
        nom = d.get("nombre") or d.get("name") or ""
        mapa[_norm(nom)] = (c.id, nom)
    return mapa


def cargar_en_kebo(usuario_id, meses, db):
    """Escribe los meses parseados en KEBO. Reescribe cada mes presente."""
    user_ref = db.collection("users").document(str(usuario_id))
    cat_map = _cat_id_por_nombre(user_ref)

    resumen = []
    for mes_key, info in sorted(meses.items()):
        tx_items = user_ref.collection("transactions").document(mes_key).collection("items")
        bg_items = user_ref.collection("budgets").document(mes_key).collection("items")

        # Reset del mes
        for d in tx_items.stream():
            d.reference.delete()
        for d in bg_items.stream():
            d.reference.delete()

        # Ingreso
        income = float(info.get("income", 0) or 0)
        if income > 0:
            sal_id = cat_map.get(_norm("Salario"), (None, "Salario"))[0]
            tx_items.document(f"income-{mes_key}").set({
                "type": "income",
                "amount": income,
                "category_id": sal_id,
                "category_name": "Salario",
                "description": f"Ingreso mensual {mes_key}",
                "status": "cleared",
                "tags": ["import-txt"],
                "date": f"{mes_key}-01",
                "created_at": datetime.now(),
            })

        # Presupuestos + gastos
        n_pres = n_gas = 0
        for nombre, (pres, gast) in info.get("budgets", {}).items():
            cat_id, cat_real = cat_map.get(_norm(nombre), (None, nombre))
            bg_items.document().set({
                "category_id": cat_id,
                "category_name": cat_real,
                "amount": float(pres),
                "year": mes_key[:4],
                "month": mes_key[5:7],
                "created_at": datetime.now(),
            })
            n_pres += 1
            if gast and gast > 0:
                tx_items.document().set({
                    "type": "expense",
                    "amount": float(gast),
                    "category_id": cat_id,
                    "category_name": cat_real,
                    "description": f"Gasto {cat_real} ({mes_key})",
                    "status": "cleared",
                    "tags": ["import-txt"],
                    "date": f"{mes_key}-15",
                    "created_at": datetime.now(),
                })
                n_gas += 1

        resumen.append({
            "mes": mes_key,
            "ingreso": income,
            "presupuestos": n_pres,
            "gastos": n_gas,
            "total_gastado": sum(g for _, g in info.get("budgets", {}).values()),
        })

    return resumen


def importar_texto(usuario_id, texto, db, anio_default=None):
    """Función de alto nivel: parsea el texto y lo carga. Devuelve reporte legible."""
    meses = parsear_reporte(texto, anio_default)
    if not meses:
        return "⚠️ No pude reconocer ningún mes/categoría en el archivo. Revisa el formato."

    # Carga a KEBO
    cargar_en_kebo(usuario_id, meses, db)

    meses_orden = sorted(meses.keys())  # YYYY-MM

    # Totales globales
    total_ing = sum(float(meses[m].get("income", 0) or 0) for m in meses_orden)
    total_gas = 0.0
    for m in meses_orden:
        for _, (pres, gast) in (meses[m].get("budgets", {}) or {}).items():
            total_gas += float(gast or 0)
    neto = total_ing - total_gas

    # Último mes importado que tenga presupuestos (para recomendaciones)
    last_month = None
    for m in reversed(meses_orden):
        if (meses[m].get("budgets", {}) or {}):
            last_month = m
            break

    excedidos_top = []
    if last_month:
        presup = meses[last_month].get("budgets", {}) or {}
        for cat, (pres, gast) in presup.items():
            pres_f = float(pres or 0)
            gast_f = float(gast or 0)
            exceso = gast_f - pres_f
            if exceso > 0:
                excedidos_top.append((exceso, cat, gast_f, pres_f))
        excedidos_top.sort(reverse=True, key=lambda x: x[0])

    lineas = ["✅ **Importación completada** (desde .txt)."]
    lineas.append(
        f"💰 Total ingresos: ${total_ing:,.0f} | 🔻 Total gastos: ${total_gas:,.0f} | 📌 Neto: ${neto:,.0f}"
    )

    # Resumen mes a mes (una sola línea por mes)
    for m in meses_orden:
        income = float(meses[m].get("income", 0) or 0)
        gastado = 0.0
        for _, (pres, gast) in (meses[m].get("budgets", {}) or {}).items():
            gastado += float(gast or 0)
        net_mes = income - gastado
        lineas.append(f"• {m}: Ingreso ${income:,.0f} | Gastado ${gastado:,.0f} | Neto ${net_mes:,.0f}")

    # Recomendación compacta
    if last_month:
        if excedidos_top:
            top = excedidos_top[:2]
            parts = []
            for exceso, cat, gast_f, pres_f in top:
                parts.append(f"{cat} (+${exceso:,.0f})")
            lineas.append("")
            lineas.append(f"🧠 Recomendación: En {last_month} excediste: {', '.join(parts)}. Prioriza ajustar esos gastos.")
        else:
            lineas.append("")
            lineas.append(f"🧠 Recomendación: En {last_month} todo está dentro del presupuesto.")

    lineas.append("")
    lineas.append("📊 Listo. Actualiza tu dashboard o el widget para ver el cambio.")
    return "\n".join(lineas)
