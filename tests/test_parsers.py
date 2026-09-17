import unittest
from modules.ai import (
    _parse_borrar_presupuesto,
    _parse_renombrar_presupuesto,
    _parse_presupuesto_multiple,
    _parse_editar_presupuesto,
    _parse_listar_categorias,
    _parse_analisis_financiero,
    _parse_sobrante,
    _parse_ajustar_balance,
    _parse_ver_presupuesto,
)
from modules.db import _coincidir_categoria, _cat_exacta, _normalizar_cat_str


class TestBorrarPresupuesto(unittest.TestCase):
    def test_borrar_multiple_con_subjuntivo_y_typo(self):
        texto = (
            "necesito q elimines los presupuestps de "
            "Necesito Q Edites Hola Yerbis Le Pongan Categoría Mamá Mamá Deuda Lo Pongas Deudas Es "
            "y el de Hola, Yerbis. Yerbis, Puedes Poner y el de mama deudas"
        )
        res = _parse_borrar_presupuesto(texto)
        self.assertIsNotNone(res)
        self.assertIn("categorias", res)
        cats = res["categorias"]
        self.assertEqual(len(cats), 3)
        self.assertTrue(any("Necesito Q Edites" in c for c in cats))
        self.assertTrue(any("Hola, Yerbis" in c for c in cats))
        self.assertTrue(any("Mama Deudas" in c for c in cats))

    def test_borrar_categoria_simple(self):
        res = _parse_borrar_presupuesto("elimina el presupuesto de comida")
        self.assertIsNotNone(res)
        self.assertEqual(res.get("categoria"), "Comida")
        self.assertEqual(res.get("categorias"), ["Comida"])

    def test_borrar_con_subjuntivo_simple(self):
        res = _parse_borrar_presupuesto("necesito que borres el presupuesto de entretenimiento")
        self.assertIsNotNone(res)
        self.assertEqual(res.get("categoria"), "Entretenimiento")

    def test_borrar_todos(self):
        res = _parse_borrar_presupuesto("borra todos los presupuestos de septiembre")
        self.assertIsNotNone(res)
        self.assertTrue(res.get("todos"))


class TestRenombrarPresupuesto(unittest.TestCase):
    def test_renombrar_enclitico_con_cambio_monto(self):
        texto = "el presupuesto de septiembre renómbralo y ponle q sea de deudas y son 205.000 no 105.000"
        res = _parse_renombrar_presupuesto(texto)
        self.assertIsNotNone(res)
        self.assertEqual(res["cat_antigua"], "Septiembre")
        self.assertEqual(res["cat_nueva"], "Deudas")
        self.assertEqual(res.get("nuevo_limite"), 205000.0)

    def test_renombrar_enclitico_simple(self):
        texto = "el presupuesto de septiembre renómbralo y ponle q sea de deudas"
        res = _parse_renombrar_presupuesto(texto)
        self.assertIsNotNone(res)
        self.assertEqual(res["cat_antigua"], "Septiembre")
        self.assertEqual(res["cat_nueva"], "Deudas")
        self.assertNotIn("nuevo_limite", res)

    def test_renombrar_directo(self):
        texto = "renombra el presupuesto de hola yerbis a mamá"
        res = _parse_renombrar_presupuesto(texto)
        self.assertIsNotNone(res)
        self.assertEqual(res["cat_antigua"], "Hola Yerbis")
        self.assertEqual(res["cat_nueva"], "Mamá")

    def test_renombrar_directo_con_monto(self):
        texto = "cambia el nombre de comida por alimentación y ponle 300k"
        res = _parse_renombrar_presupuesto(texto)
        self.assertIsNotNone(res)
        self.assertEqual(res["cat_antigua"], "Comida")
        self.assertEqual(res["cat_nueva"], "Alimentación")
        self.assertEqual(res.get("nuevo_limite"), 300000.0)


class TestPresupuestoMultipleGuard(unittest.TestCase):
    def test_no_crea_presupuesto_en_renombrado_complejo(self):
        texto = "el presupuesto de septiembre renómbralo y ponle q sea de deudas y son 205.000 no 105.000"
        res = _parse_presupuesto_multiple(texto)
        self.assertIsNone(res)

    def test_no_crea_presupuesto_en_eliminacion(self):
        texto = "elimina el presupuesto de comida de 100k"
        res = _parse_presupuesto_multiple(texto)
        self.assertIsNone(res)

    def test_creacion_multiple_valida(self):
        texto = "establece presupuestos mamá 150.000, deudas 205.000 para septiembre 2026"
        res = _parse_presupuesto_multiple(texto)
        self.assertIsNotNone(res)
        self.assertEqual(len(res), 2)
        cats = {p["categoria"]: p["limite"] for p in res}
        self.assertEqual(cats["Mamá"], 150000.0)
        self.assertEqual(cats["Deudas"], 205000.0)

    def test_rechazo_categoria_con_digitos(self):
        texto = "presupuesto son 205.000 no 105.000"
        res = _parse_presupuesto_multiple(texto)
        if res:
            for p in res:
                self.assertNotIn("205", p["categoria"])


class TestCoincidirCategoria(unittest.TestCase):
    def test_exacta_insensible_acentos_y_puntuacion(self):
        self.assertTrue(_cat_exacta("Mamá", "mama"))
        self.assertTrue(_cat_exacta("Septiembre.", "septiembre"))
        self.assertTrue(_cat_exacta("Mamá Deudas,", "mama deudas"))

    def test_diferencia_exacta_entre_subsets(self):
        # "Mamá" no debe ser exactamente igual a "Mamá Deudas"
        self.assertFalse(_cat_exacta("Mamá", "Mamá Deudas"))
        self.assertFalse(_cat_exacta("Mamá Deudas", "Mamá"))

    def test_coincidencia_parcial(self):
        # Pero sí debe coincidir difusamente si no hay exacta
        self.assertTrue(_coincidir_categoria("Mamá Deudas", "deudas"))
        self.assertTrue(_coincidir_categoria("Mamá Deudas", "mama"))


class TestConsultasFinancieras(unittest.TestCase):
    """Tests para los nuevos parsers de v3.2"""

    def test_listar_categorias(self):
        self.assertTrue(_parse_listar_categorias("q categorias hay"))
        self.assertTrue(_parse_listar_categorias("cuales categorias hay"))
        self.assertTrue(_parse_listar_categorias("lista categorias"))
        self.assertFalse(_parse_listar_categorias("presupuesto de categoría"))

    def test_analisis_financiero(self):
        self.assertTrue(_parse_analisis_financiero("dame una analisis financiero"))  # typo ok
        self.assertTrue(_parse_analisis_financiero("análisis financiero"))
        self.assertTrue(_parse_analisis_financiero("reporte mensual"))
        self.assertFalse(_parse_analisis_financiero("presupuesto de septiembre"))

    def test_sobrante(self):
        self.assertTrue(_parse_sobrante("deja lo que sobra"))
        self.assertTrue(_parse_sobrante("sobrante"))
        self.assertTrue(_parse_sobrante("excedente"))
        self.assertFalse(_parse_sobrante("presupuesto de comida"))

    def test_ajustar_balance(self):
        self.assertTrue(_parse_ajustar_balance("ajustar mi balance a los presupuestos"))
        self.assertTrue(_parse_ajustar_balance("ajustar mi balance a los presupuestos de septiembre"))
        self.assertFalse(_parse_ajustar_balance("ver presupuestos"))

    def test_ver_presupuesto_requiere_consulta(self):
        # Debe tener palabra de consulta + presupuesto
        self.assertTrue(_parse_ver_presupuesto("dame los presupuestos"))
        self.assertTrue(_parse_ver_presupuesto("ver presupuestos"))
        self.assertTrue(_parse_ver_presupuesto("hay presupuestos?"))
        # Sin palabra de consulta, no se dispara
        self.assertFalse(_parse_ver_presupuesto("ajustar mi balance a los presupuestos"))
        self.assertFalse(_parse_ver_presupuesto("presupuesto comida 150k"))  # es crear


if __name__ == "__main__":
    unittest.main()

