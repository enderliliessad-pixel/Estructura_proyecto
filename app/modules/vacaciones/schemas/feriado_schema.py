from datetime import date

from pydantic import BaseModel, ConfigDict

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
