# Limpieza y Estructura Simplificada — JARVIS

> **Fecha:** 2026-10-09  
> **Estado:** Completado  
> **Propósito:** Documentar la purga masiva y la consolidación a la topología simplificada final.

---

## 1. Resumen de Carpetas y Archivos Borrados

| Directorio / Archivo | Tipo | Justificación de Eliminación |
|---|---|---|
| `dataconnect/` | Google Cloud Data Connect | Esquemas huérfanos; `inicializar_sql()` nunca llamado en código Python |
| `memory/` | Documentación markdown | `split-kebo-presupuestos.md` sin referencias en `.py` |
| `plans/` | Documentación markdown | `limpieza-presupuestos-sep2026.md` sin referencias en `.py` |
| `app/router/` | Paquete vacío | `__init__.py` de 0 líneas; sin imports en todo el códigobase |
| `path/` | Estructura vacía | `to/` sin contenido funcional |
| `temp_audios/` | Directorio vacío | Sin archivos de audio persistentes |
| `docs/` | 3 archivos markdown | `api-endpoints.md`, `architecture.md`, `database-schema.md` sin referencias en `.py` |
| `scripts/` | 8 scripts utilitarios | Scripts de setup, test y mantenimiento sin uso en producción |

**Total eliminado:** 8 directorios, 12 archivos (markdown + scripts).

---

## 2. Justificación de la Topología Simplificada

### Arquitectura Aplicada: Atomic Design + FastAPI

La estructura resultante sigue un patrón de **Diseño Atómico** en 5 capas jerárquicas (`app/core/`):

1. **Átoms** (`app/core/atoms/formatters.py`) — Formateadores puros, sin efectos secundarios.
2. **Molecules** (`app/core/molecules/cards.py`) — Componentes ensamblados a partir de átomos.
3. **Organisms** (`app/core/organisms/finance_organism.py`) — Lógica de negocio con inyección de dependencias.
4. **Templates** (`app/core/templates/telegram_templates.py`) — Plantillas de respuesta reutilizables.
5. **Routes** (`app/routes/telegram.py`, etc.) — Puntos de entrada ASGI que consumen las capas inferiores.

### Beneficios de esta Consolidación

| Objetivo | Resultado |
|---|---|
| **Reducción de dependencias** | 8 directorios eliminados con 0 referencias runtime; solo `src/` y `app/services/` conservados |
| **Mantenibilidad** | Cada capa es testeable de forma aislada; cambios en formato de moneda solo tocan `atomo_formatear_moneda()` |
| **Escalabilidad** | Nuevos organismos pueden agregarse sin tocar las capas inferiores |
| **Claridad operativa** | La ruta de entrada (`app/routes/telegram.py`) orquesta sin contener lógica de negocio ni formato |
| **Despliegue Vercel** | Funciones serverless más ligeras al no cargar módulos legacy no utilizados |

La topología restante (`app/`, `modules/`, `src/`, `tests/`, `widgets/`) mantiene la lógica de negocio activa, integraciones externas y la batería de pruebas unitarias sin alteraciones en su funcionamiento.

---

## 3. Enlaces Wiki Obligatorios

- `[[Jarvis/estado_proyecto.md]]` — Bitácora de avances y roadmap.
- `[[Índice Principal.md]]` — Navegación global del proyecto.
- `[[README.md]]` — Documentación oficial consolidada.

---

## 4. Diagrama de Flujo Post-Purga

```
app/
├── core/          # Atomic Design (atoms, molecules, organisms, templates)
├── routes/        # FastAPI endpoints (telegram, widgets, kebo, prestamos, services)
├── api.py         # api_router consolidado
└── main.py        # Punto de entrada ASGI
```

---