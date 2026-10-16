import unittest
from unittest.mock import patch

from modules.finance.advisor import (
    calcular_propuesta_presupuesto,
    generar_mensaje_propuesta,
)
from modules.finance.interceptor import (
    _detectar_mes_en_texto,
    detectar_e_interactuar_finanzas,
)


class TestFinanceAdvisor(unittest.TestCase):
    def test_proposal_uses_four_recent_active_firestore_months(self):
        summaries = {
            "2026-09": {
                "status": "ok",
                "total_ingresos": 0,
                "total_gastos": 0,
                "gastos_por_categoria": {},
            },
            "2026-08": {
                "status": "ok",
                "total_ingresos": 800,
                "total_gastos": 300,
                "gastos_por_categoria": {"alimentacion": 200, "moto": 100},
            },
            "2026-07": {
                "status": "ok",
                "total_ingresos": 700,
                "total_gastos": 400,
                "gastos_por_categoria": {"alimentacion": 250, "moto": 150},
            },
            "2026-06": {
                "status": "ok",
                "total_ingresos": 0,
                "total_gastos": 500,
                "gastos_por_categoria": {"alimentacion": 300, "deudas": 200},
            },
            "2026-05": {
                "status": "ok",
                "total_ingresos": 900,
                "total_gastos": 600,
                "gastos_por_categoria": {"alimentacion": 400, "deudas": 200},
            },
        }

        with patch(
            "modules.finance.advisor.obtener_resumen_dashboard",
            side_effect=lambda _usuario, mes: summaries[mes],
        ) as obtener_resumen:
            proposal = calcular_propuesta_presupuesto("octubre 2026")

        self.assertEqual(
            proposal["meses_historial"],
            ["2026-08", "2026-07", "2026-06", "2026-05"],
        )
        self.assertEqual(proposal["ingreso_proyectado"], 800)
        self.assertEqual(
            proposal["topes_sugeridos"],
            {"alimentacion": 287.5, "deudas": 100.0, "moto": 62.5},
        )
        self.assertEqual(proposal["total_gastos_sugeridos"], 450)
        self.assertEqual(proposal["ahorro_inversion_sugerido"], 350)
        self.assertEqual(obtener_resumen.call_count, 5)

    def test_no_history_does_not_invent_income_or_budget(self):
        with patch(
            "modules.finance.advisor.obtener_resumen_dashboard",
            return_value={
                "status": "ok",
                "total_ingresos": 0,
                "total_gastos": 0,
                "gastos_por_categoria": {},
            },
        ):
            proposal = calcular_propuesta_presupuesto("2026-10")

        self.assertEqual(proposal["status"], "sin_historial")
        self.assertNotIn("ingreso_proyectado", proposal)
        self.assertIn("no tiene meses anteriores", generar_mensaje_propuesta(proposal))

    def test_expense_only_history_does_not_invent_income(self):
        with patch(
            "modules.finance.advisor.obtener_resumen_dashboard",
            return_value={
                "status": "ok",
                "total_ingresos": 0,
                "total_gastos": 100,
                "gastos_por_categoria": {"moto": 100},
            },
        ):
            proposal = calcular_propuesta_presupuesto("2026-10")

        self.assertEqual(proposal["status"], "sin_historial_ingresos")
        self.assertIn("no voy a", generar_mensaje_propuesta(proposal).lower())

    def test_telegram_advice_phrase_uses_advisor_before_month_summary(self):
        with (
            patch(
                "modules.finance.interceptor.calcular_propuesta_presupuesto",
                return_value={"status": "ok", "mes_destino": "Octubre 2026"},
            ) as calcular,
            patch(
                "modules.finance.interceptor.generar_mensaje_propuesta",
                return_value="Propuesta basada en historial",
            ) as generar,
            patch("modules.finance.interceptor.obtener_resumen_dashboard") as resumen,
        ):
            result = detectar_e_interactuar_finanzas(
                "cuáles presupuesto debería asignar en octubre"
            )

        self.assertEqual(result, "Propuesta basada en historial")
        calcular.assert_called_once_with("2026-10")
        generar.assert_called_once()
        resumen.assert_not_called()

    def test_budget_status_question_still_uses_live_month_summary(self):
        with (
            patch(
                "modules.finance.interceptor.calcular_propuesta_presupuesto"
            ) as calcular,
            patch(
                "modules.finance.interceptor.obtener_resumen_dashboard",
                return_value={
                    "status": "ok",
                    "mes": "Agosto 2026",
                    "total_limite": 100,
                    "total_gastos": 25,
                    "total_ingresos": 200,
                    "porcentaje_uso": 25,
                    "total_libre": 75,
                    "datos_por_categoria": [],
                },
            ) as resumen,
        ):
            result = detectar_e_interactuar_finanzas("qué presupuesto tengo")

        self.assertIn("Agosto 2026", result)
        calcular.assert_not_called()
        resumen.assert_called_once_with(mes=None)

    def test_month_parser_honors_explicit_year(self):
        self.assertEqual(_detectar_mes_en_texto("presupuesto de octubre 2027"), "2027-10")


if __name__ == "__main__":
    unittest.main()
