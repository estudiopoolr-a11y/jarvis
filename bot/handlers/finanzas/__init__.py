"""bot/handlers/finanzas/__init__.py - Punto de entrada para comandos financieros.

Este paquete contiene todos los comandos relacionados con finanzas,
organizados por responsabilidad:
- balance: Comandos de balance general y estadísticas
- presupuestos: Comandos de gestión de presupuestos
- historial: Comandos de historial y búsqueda de transacciones
"""
from bot.handlers.finanzas.balance import ver_finanzas, ver_mes, ver_stats
from bot.handlers.finanzas.presupuestos import ver_presupuestos
from bot.handlers.finanzas.historial import ver_historial, buscar_categoria, ver_top

__all__ = [
    'ver_finanzas',
    'ver_presupuestos',
    'ver_historial',
    'buscar_categoria',
    'ver_mes',
    'ver_stats',
    'ver_top',
]
