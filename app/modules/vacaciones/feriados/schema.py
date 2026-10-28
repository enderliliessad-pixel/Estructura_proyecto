from datetime import date

from pydantic import BaseModel, ConfigDict, Field

# esquema para verificar el formato 
class FeriadoRespuesta(BaseModel):
    # se va a configurar el esquema 
    # para que la web pueda leerlo como tipo json gracias al from_attributes=True
    model_config = ConfigDict(from_attributes=True)
    # estructura del json con los siguientes atributos
    id_feriado: int
    fecha: date | None
    descripcion: str | None
    tipo: str | None
    estado: bool | None


# datos del calendario; no determinan todavía el descuento de vacaciones
class FeriadoDatos(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    fecha: date
    descripcion: str = Field(min_length=1, max_length=200)
    tipo: str = Field(min_length=1, max_length=100)

# clase para validar los datos al crear un feriado
# hereda la fecha, descripcion y tipo de FeriadoDatos
class FeriadoCrear(FeriadoDatos):
    estado: bool = Field(default=True, strict=True)

# clase para validar los datos al actualizar un feriado
class FeriadoActualizar(FeriadoDatos):
    # reemplaza fecha, descripción y tipo; el estado se cambia por separado
    pass

# clase para validar el cambio de estado de un feriado
class FeriadoEstado(BaseModel):
    # rechazamos cualquier campo adicional que no este definido en esta clase
    model_config = ConfigDict(extra="forbid")
    # el estado es obligatorio porque no tiene un valor por defecto
    # solo acepta true para activar o false para desactivar
    estado: bool = Field(strict=True)
