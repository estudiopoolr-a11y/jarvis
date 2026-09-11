from modules.importador_txt import parsear_reporte

texto = """1. INGRESOS POR MES (Año 2026):
- Mayo: $1.061.159,03
- Junio: $1.058.894,26
- Julio: $936.455,00
- Agosto: $806.199,03

--- AGOSTO 2026 ---
- Alimentación: Presupuestado $150.000,00 | Gastado $150.000,00
- Madre: Presupuestado $50.000,00 | Gastado $50.000,00
"""
resultado = parsear_reporte(texto, 2026)
assert resultado["2026-05"]["income"] == 1061159.03
assert resultado["2026-06"]["income"] == 1058894.26
assert resultado["2026-07"]["income"] == 936455.0
assert resultado["2026-08"]["income"] == 806199.03
assert resultado["2026-08"]["budgets"]["Alimentación"] == (150000.0, 150000.0)
assert resultado["2026-08"]["budgets"]["Madre"] == (50000.0, 50000.0)
print("OK: parser TXT financiero")
