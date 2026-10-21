from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# esquema para verificar el formato 
class SolicitudRespuesta(BaseModel):
    # se va a configurar el esquema 
    # para que la web pueda leerlo como tipo json gracias al from_attributes=True
    model_config = ConfigDict(from_attributes=True)
    # estructura del json con los siguientes atributos
    id_solicitud: int
    id_empleado: int | None
    tipo: str | None
    fecha_inicio: date | None
    fecha_fin: date | None
    dias_solicitados: Decimal | None
    horas_solicitadas: Decimal | None
    motivo: str | None
    estado: str | None
    fecha_solicitud: datetime | None
