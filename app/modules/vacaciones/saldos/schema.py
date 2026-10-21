from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# esquema para verificar el formato 
class SaldoRespuesta(BaseModel):
    # se va a configurar el esquema 
    # para que la web pueda leerlo como tipo json gracias al from_attributes=True
    model_config = ConfigDict(from_attributes=True)
    # estructura del json con los siguientes atributos
    id_saldo: int
    id_empleado: int | None
    periodo: str | None
    dias_asignados: Decimal | None
    dias_utilizados: Decimal | None
    dias_disponibles: Decimal | None
