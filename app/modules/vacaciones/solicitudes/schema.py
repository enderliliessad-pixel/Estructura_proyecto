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
    dias_solicitados: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=2)
    motivo: str = Field(min_length=1)
     # ejecutamos esta validacion despues de validar los campos del modelo
    @model_validator(mode="after")
    # self representa la instancia que estamos validando
    # Self indica que devolvemos una instancia de esta misma clase
    def validar_fechas(self) -> Self:
        # comprobamos que la fecha final no sea anterior a la inicial
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")
        # devolvemos la instancia validada para continuar con el proceso
        return self

# clase para validar los datos al crear una solicitud
class SolicitudCrear(SolicitudDatos):
    id_empleado: int = Field(strict=True, ge=1, le=9223372036854775807)
    tipo: Literal["VACACIONES"] = "VACACIONES"
    # Esta operación registra vacaciones en días; los permisos van aparte.
    horas_solicitadas: Decimal = Field(default=Decimal("0.00"), ge=0, le=0)

# clase para validar los datos al actualizar una solicitud
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
