from typing import Literal

from pydantic import BaseModel

# clase que define el estado de la base para la conexion
class EstadoRespuesta(BaseModel):
    estado: Literal["ok"] = "ok"
    mensaje: str

