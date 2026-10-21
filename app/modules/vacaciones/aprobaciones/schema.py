from datetime import datetime

from pydantic import BaseModel, ConfigDict

# esquema para verificar el formato 
class AprobacionRespuesta(BaseModel):
    # se va a configurar el esquema 
    # para que la web pueda leerlo como tipo json gracias al from_attributes=True
    model_config = ConfigDict(from_attributes=True)
    # estructura del json con los siguientes atributos
    id_aprobacion: int
    id_solicitud: int | None
    id_aprobador: int | None
    fecha: datetime | None
    decision: str | None
    observacion: str | None
