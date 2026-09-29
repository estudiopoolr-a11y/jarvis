"""Conexión PostgreSQL para Firebase Data Connect.

La base documental sigue siendo Cloud Firestore. Las operaciones de negocio
usan este cliente SQL (Cloud SQL) y el esquema de dataconnect/schema/.
"""
from __future__ import annotations

import os
from pathlib import Path

USUARIO_PRINCIPAL = "1536228767180136498"
_READY = False


def database_url() -> str:
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("DATA_CONNECT_POSTGRES_URL")
        or os.getenv("FIREBASE_DATA_CONNECT_URL")
        or ""
    )


def connect():
    """Abre una conexión PostgreSQL. Requiere psycopg y DATABASE_URL."""
    url = database_url()
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. Apunta al Postgres de Firebase Data Connect."
        )
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(url, row_factory=dict_row)


def resolver_usuario(usuario_id="default") -> str:
    if not usuario_id or str(usuario_id) in ("default", "iphone_user", "None", ""):
        return USUARIO_PRINCIPAL
    return str(usuario_id)


def inicializar_sql(force: bool = False) -> bool:
    """Crea las tablas relacionales si todavía no existen."""
    global _READY
    if _READY and not force:
        return True
    schema = Path(__file__).resolve().parents[2] / "dataconnect" / "schema" / "schema.sql"
    if not schema.exists():
        raise FileNotFoundError(f"No se encontró el esquema SQL: {schema}")
    statements = _statements(schema.read_text(encoding="utf-8"))
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            for statement in statements:
                cur.execute(statement)
    _READY = True
    return True


def _statements(script: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            chunks.append("\n".join(current))
            current = []
    if current:
        chunks.append("\n".join(current))
    return chunks


def fetchall(sql: str, params: tuple = ()):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return []
            return list(cur.fetchall())


def fetchone(sql: str, params: tuple = ()):
    rows = fetchall(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone() if cur.description else None
            affected = cur.rowcount
    return row, affected
