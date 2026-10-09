# Módulo de Organismos: Coordinación de moléculas y fuentes de datos Kebo #
from app.core.molecules.cards import molecula_tarjeta_balance, molecula_tarjeta_presupuesto  # Importar moléculas de tarjetas #

class OrganismoFinanzas:  # Clase contenedora de la lógica de finanzas atómica #
    """Organismo que orquesta la obtención y presentación de datos financieros."""

    def __init__(self, db_connector=None):  # Inicializador con inyección opcional de BD #
        self.db = db_connector  # Asignar conector de base de datos inyectado #

    async def obtener_resumen_organismo(self, user_id: str = "default") -> str:  # Método asíncrono para generar resumen financiero #
        """
        Orquesta la consulta de datos financieros y retorna una tarjeta formateada.
        En producción, reemplazar valores de prueba por consultas reales a Kebo API / Firestore.
        """
        # TODO: Reemplazar valores hardcoded por consulta real a Firestore/Kebo cuando db_connector esté disponible #
        saldo_real = 1500000.0  # Simular saldo consolidado de todas las cuentas #
        gastos_reales = 450000.0  # Simular gastos del mes actual #
        limite_real = 1000000.0  # Simular límite presupuestal mensual #
        return molecula_tarjeta_balance(saldo_real, gastos_reales, limite_real)  # Retornar mensaje ensamblado desde molécula #

    async def obtener_detalle_presupuestos(self, user_id: str = "default") -> str:  # Método asíncrono para detalle por categoría #
        """
        Orquesta la consulta de presupuestos por categoría y retorna bloques formateados.
        En producción, reemplazar valores de prueba por consultas reales a Firestore.
        """
        # TODO: Implementar consulta real a colección budgets de Firestore cuando db_connector esté disponible #
        resultados = []  # Lista acumuladora de tarjetas por categoría #
        categorias = [  # Lista de categorías con datos simulados para prototipo #
            {"categoria": "Alimentación", "asignado": 300000, "gastado": 180000, "limite": 300000},
            {"categoria": "Transporte", "asignado": 150000, "gastado": 140000, "limite": 150000},
            {"categoria": "Entretenimiento", "asignado": 100000, "gastado": 30000, "limite": 100000},
        ]
        for cat in categorias:  # Iterar sobre cada categoría para generar su tarjeta #
            tarjeta = molecula_tarjeta_presupuesto(
                cat["categoria"],
                cat["asignado"],
                cat["gastado"],
                cat["limite"]
            )  # Ensamblar molécula de presupuesto por categoría #
            resultados.append(tarjeta)  # Acumular tarjeta en lista de resultados #
        return "\n\n".join(resultados)  # Unir todas las tarjetas separadas por doble newline #
