"""FastAPI application instance."""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="JARVIS Control Center")
USUARIO_PRINCIPAL = "1536228767180136498"


class ComandoPayload(BaseModel):
    texto: str
    usuario_id: str = USUARIO_PRINCIPAL
