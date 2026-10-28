from datetime import date
from decimal import Decimal
from pydantic import BaseModel

# clase para calcular los dias
class CalculoDiasRespuesta(BaseModel):
    fecha_inicio: date
    # último día de ausencia; no es la fecha de reincorporación
    fecha_fin: date
    dias_calendario: int
    feriados_excluidos: list[date]
    dias_vacaciones: Decimal
