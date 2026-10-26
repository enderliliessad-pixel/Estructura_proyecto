from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self


from pydantic import BaseModel, ConfigDict, Field, model_validator


# Campos al registrar y corregir una solicitud.
class SolicitudDatos(BaseModel):
    # Rechazamos campos adicionales, como estado o fecha_solicitud.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    fecha_inicio: date
    fecha_fin: date
    dias_solicitados: Decimal = Field(gt=0, max_digits=6, decimal_places=2)
    motivo: str = Field(min_length=1)

    @model_validator(mode="after")
    def validar_fechas(self) -> Self:
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")
        return self

# clase para crar una solicitud
class SolicitudCrear(SolicitudDatos):
    id_empleado: int = Field(strict=True, ge=1, le=9223372036854775807)
    tipo: Literal["VACACIONES"] = "VACACIONES"
    # Esta operación registra vacaciones en días; los permisos van aparte.
    horas_solicitadas: Decimal = Field(default=Decimal("0.00"), ge=0, le=0)

# clase para actualizar datos
class SolicitudActualizar(SolicitudDatos):
    # Hereda únicamente fechas, días y motivo; no admite cambiar al empleado.
    pass

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
