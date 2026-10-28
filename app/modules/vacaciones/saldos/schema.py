from datetime import date
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

    fecha_inicio_periodo: date | None = None
    fecha_fin_periodo: date | None = None
    fecha_acreditacion: date | None = None

# clase para definir la respuesta del resumen de saldo de un empleado
class ResumenSaldoRespuesta(BaseModel):
    id_empleado: int
    fecha_consulta: date
    total_disponible: Decimal
    periodos_acreditados: list[SaldoRespuesta]
    periodos_no_acreditados: list[SaldoRespuesta]

# clase para mostrar cuanto se tomaria de un saldo sin realizar el descuento
class DescuentoPrevisto(BaseModel):
    id_saldo: int
    periodo: str | None
    dias_disponibles: Decimal
    dias_a_descontar: Decimal
    saldo_resultante: Decimal

# clase para mostrar si el saldo alcanza y como se repartirian los descuentos
class PrevisionRespuesta(BaseModel):
    id_empleado: int
    fecha_consulta: date
    dias_solicitados: Decimal
    feriados_excluidos: list[date]
    total_disponible: Decimal
    saldo_suficiente: bool
    dias_sin_cobertura: Decimal
    descuentos: list[DescuentoPrevisto]
    advertencia: str = (
        "Previsión con saldos acreditados a la fecha de consulta. No reserva ni descuenta días; "
        "no autoriza anticipos. Se deberá recalcular al realizar el descuento efectivo."
    )
