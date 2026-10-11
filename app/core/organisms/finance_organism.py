# Módulo de Organismos: Coordinación de moléculas y fuentes de datos Kebo #
from app.core.molecules.cards import molecula_tarjeta_balance, molecula_tarjeta_presupuesto  # Importar moléculas de tarjetas #
from modules.db import obtener_balance_financiero, obtener_resumen_presupuestos  # Importar funciones de balance real #

class OrganismoFinanzas:  # Clase contenedora de la lógica de finanzas atómica #
    """Organismo que orquesta la obtención y presentación de datos financieros."""

    def __init__(self, db_connector=None):  # Inicializador con inyección opcional de BD #
        self.db = db_connector  # Asignar conector de base de datos inyectado #

    async def obtener_resumen_organismo(self, user_id: str = "default") -> str:  # Método asíncrono para generar resumen financiero #
        """
        Orquesta la consulta de datos financieros y retorna una tarjeta formateada.
        En producción, reemplazar valores de prueba por consultas reales a Kebo API / Firestore.
        """
        # Consulta real a Firebase para obtener balance consolidado
        try:
            balance, ingresos, gastos, _ = await obtener_balance_financiero(user_id)
            limite_real = 1000000.0  # Límite presupuestal mensual (configurable)
            return molecula_tarjeta_balance(balance, gastos, limite_real)
        except Exception as e:
            # Fallback a valores por defecto si falla la consulta a Firebase
            print(f"[OrganismoFinanzas] Error consultando Firebase: {e}")
            saldo_real = 1500000.0  # Simular saldo consolidado de todas las cuentas #
            gastos_reales = 450000.0  # Simular gastos del mes actual #
            limite_real = 1000000.0  # Simular límite presupuestal mensual #
            return molecula_tarjeta_balance(saldo_real, gastos_reales, limite_real)

    async def obtener_detalle_presupuestos(self, user_id: str = "default") -> str:  # Método asíncrono para detalle por categoría #
        """
        Orquesta la consulta de presupuestos por categoría y retorna bloques formateados.
        En producción, reemplazar valores de prueba por consultas reales a Firestore.
        """
        # Consulta real a Firebase para obtener presupuestos por categoría
        try:
            presupuestos = await obtener_resumen_presupuestos(user_id)
            resultados = []  # Lista acumuladora de tarjetas por categoría #
            if presupuestos:
                for categoria, datos in presupuestos.items():
                    asignado = datos.get("asignado", 0)
                    gastado = datos.get("gastado", 0)
                    tarjeta = molecula_tarjeta_presupuesto(
                        categoria,
                        asignado,
                        gastado,
                        asignado  # límite = asignado
                    )
                    resultados.append(tarjeta)
            else:
                # Fallback a categorías por defecto si no hay datos en Firebase
                categorias = [
                    {"categoria": "Alimentación", "asignado": 300000, "gastado": 180000, "limite": 300000},
                    {"categoria": "Transporte", "asignado": 150000, "gastado": 140000, "limite": 150000},
                    {"categoria": "Entretenimiento", "asignado": 100000, "gastado": 30000, "limite": 100000},
                ]
                for cat in categorias:
                    tarjeta = molecula_tarjeta_presupuesto(
                        cat["categoria"],
                        cat["asignado"],
                        cat["gastado"],
                        cat["limite"]
                    )
                    resultados.append(tarjeta)
            return "\n\n".join(resultados)
        except Exception as e:
            # Fallback a valores por defecto si falla la consulta a Firebase
            print(f"[OrganismoFinanzas] Error consultando presupuestos Firebase: {e}")
            categorias = [
                {"categoria": "Alimentación", "asignado": 300000, "gastado": 180000, "limite": 300000},
                {"categoria": "Transporte", "asignado": 150000, "gastado": 140000, "limite": 150000},
                {"categoria": "Entretenimiento", "asignado": 100000, "gastado": 30000, "limite": 100000},
            ]
            resultados = []
            for cat in categorias:
                tarjeta = molecula_tarjeta_presupuesto(
                    cat["categoria"],
                    cat["asignado"],
                    cat["gastado"],
                    cat["limite"]
                )
                resultados.append(tarjeta)
            return "\n\n".join(resultados)