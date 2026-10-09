# Módulo de Moléculas: Ensamblado de átomos en componentes visuales #
from app.core.atoms.formatters import atomo_formatear_moneda, atomo_obtener_emoji_estado  # Importar átomos formateadores #

def molecula_tarjeta_balance(saldo: float, gastos: float, limite: float) -> str:  # Molécula para bloque de saldo #
    """Ensambla una tarjeta de balance usando átomos de formato y emoji."""
    porcentaje = (gastos / limite * 100) if limite > 0 else 0.0  # Calcular porcentaje de presupuesto consumido #
    emoji = atomo_obtener_emoji_estado(porcentaje)  # Obtener emoji utilizando el átomo semafórico #
    saldo_txt = atomo_formatear_moneda(saldo)  # Formatear saldo con átomo de moneda #
    gastos_txt = atomo_formatear_moneda(gastos)  # Formatear gastos con átomo de moneda #
    return f"{emoji} *Balance*: {saldo_txt}\n📉 *Gastos del Mes*: {gastos_txt} ({porcentaje:.1f}%)"  # Retornar bloque Markdown #

def molecula_tarjeta_presupuesto(categoria: str, asignado: float, gastado: float, limite: float) -> str:  # Molécula para bloque de presupuesto por categoría #
    """Ensambla una tarjeta de presupuesto para una categoría específica."""
    porcentaje = (gastado / limite * 100) if limite > 0 else 0.0  # Calcular porcentaje consumido de la categoría #
    emoji = atomo_obtener_emoji_estado(porcentaje)  # Obtener emoji semafórico para la categoría #
    asignado_txt = atomo_formatear_moneda(asignado)  # Formatear monto asignado con átomo de moneda #
    gastado_txt = atomo_formatear_moneda(gastado)  # Formatear monto gastado con átomo de moneda #
    restante_txt = atomo_formatear_moneda(max(0, limite - gastado))  # Calcular y formatear lo restante #
    return f"{emoji} *{categoria}*\n💰 *Asignado*: {asignado_txt}\n📉 *Gastado*: {gastado_txt} ({porcentaje:.1f}%)\n✅ *Disponible*: {restante_txt}"  # Retornar bloque Markdown estructurado #
