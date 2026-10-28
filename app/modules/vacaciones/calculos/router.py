from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import obtener_sesion
from app.modules.vacaciones.calculos.schema import CalculoDiasRespuesta
from app.modules.vacaciones.calculos.service import calcular_dias_vacaciones

router = APIRouter(prefix="/calculos", tags=["Cálculos"])

# documentacion para indicar que a traves de los dias que l usuario coloque vea si tiene el saldo para poder realizar sus vacaciones
@router.get(
    "/dias", response_model=CalculoDiasRespuesta,
    summary="Calcular días de vacaciones sin registrar una solicitud",
    description=(
        "Incluye las fechas inicial y final y los fines de semana; excluye fechas únicas de "
        "feriados activos registrados. fecha_fin es el último día de ausencia, no el regreso. "
        "El resultado depende de que el calendario de feriados esté completo y sea aplicable al trabajador."
    ),
)
# funcion para calcular los dias
async def consultar_calculo_dias(
    fecha_inicio: date, fecha_fin: date,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> CalculoDiasRespuesta:
    return await calcular_dias_vacaciones(sesion, fecha_inicio, fecha_fin)
