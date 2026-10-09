# Módulo de Átomos: Formateadores puros y utilidades básicas #
def atomo_formatear_moneda(monto: float) -> str:  # Átomo para convertir números en formato de moneda COP #
    """Convierte un monto numérico a string formateado en pesos colombianos."""
    return f"${monto:,.0f} COP".replace(",", ".")  # Retornar string estructurado con separadores de miles #

def atomo_obtener_emoji_estado(porcentaje: float) -> str:  # Átomo para determinar emoji semafórico #
    """Retorna emoji semafórico según porcentaje de presupuesto consumido."""
    if porcentaje > 90.0:  # Evaluar si sobrepasó el límite crítico #
        return "🔴"  # Retornar indicador rojo de alerta #
    elif porcentaje > 75.0:  # Evaluar si está en rango de precaución #
        return "🟡"  # Retornar indicador amarillo #
    return "🟢"  # Retornar indicador verde por defecto #
