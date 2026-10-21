from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# esquema para verificar el formato 
class PermisoRespuesta(BaseModel):
    # se va a configurar el esquema 
    # para que la web pueda leerlo como tipo json gracias al from_attributes=True
    model_config = ConfigDict(from_attributes=True)
    # estructura del json con los siguientes atributos
    id_permiso: int
    id_empleado: int | None
    fecha: date | None
    hora_inicio: time | None
    hora_fin: time | None
    total_horas: Decimal | None
    motivo: str | None
    estado: str | None
