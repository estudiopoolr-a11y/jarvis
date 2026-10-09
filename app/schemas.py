from pydantic import BaseModel

USUARIO_PRINCIPAL = "1536228767180136498"

class ComandoPayload(BaseModel):
    texto: str
    usuario_id: str = USUARIO_PRINCIPAL
