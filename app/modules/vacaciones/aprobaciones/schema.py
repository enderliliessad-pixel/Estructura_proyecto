from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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


# datos necesarios para registrar el rechazo de una solicitud
class RechazoCrear(BaseModel):
    # Prohíbe campos adicionales y limpia espacios en blanco en strings
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id_aprobador: int = Field(strict=True, ge=1, le=9223372036854775807)
    # Comentario u observación obligatoria de la aprobación
    observacion: str = Field(min_length=1)

# datos para registrar la aprobacion final de talento humano
class AprobacionCrear(BaseModel):
    # Prohíbe campos adicionales y limpia espacios en blanco en strings
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id_aprobador: int = Field(strict=True, ge=1, le=9223372036854775807)
    # Comentario u observación obligatoria de la aprobación
    observacion: str = Field(min_length=1)
