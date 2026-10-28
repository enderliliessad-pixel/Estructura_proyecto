from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

# esquema para consultar las reservas activas y el historial de sus cambios
class ReservaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_reserva: int
    id_solicitud: int
    id_saldo: int
    dias_reservados: Decimal
    es_anticipo: bool
    estado: str
    fecha_registro: datetime
    fecha_cierre: datetime | None
