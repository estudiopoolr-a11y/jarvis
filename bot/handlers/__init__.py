"""bot.handlers - Paquete de comandos Discord de JARVIS.

Cada submódulo contiene comandos relacionados con una funcionalidad específica.
Los comandos se registran automáticamente al importar el módulo.
"""
from . import finanzas  # noqa: F401 - Comandos financieros (balance, presupuestos, historial)
from . import mantenimiento  # noqa: F401 - Comandos de mantenimiento del sistema
from . import metas  # noqa: F401 - Comandos de gestión de metas
from . import pagos  # noqa: F401 - Comandos de gestión de pagos
from . import presupuestos  # noqa: F401 - Comandos adicionales de presupuestos
from . import sistema  # noqa: F401 - Comandos del sistema
from . import tareas  # noqa: F401 - Comandos de gestión de tareas
