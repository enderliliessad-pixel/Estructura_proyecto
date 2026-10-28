from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.vacaciones.feriados.repository import consultar_fechas_feriados
from app.modules.vacaciones.calculos.schema import CalculoDiasRespuesta
from app.modules.vacaciones.solicitudes.schema import SolicitudDatos

# funcion para calcular los dias de vacaciones y devolver el detalle del calculo
async def calcular_dias_vacaciones(
    sesion: AsyncSession, fecha_inicio: date, fecha_fin: date
) -> CalculoDiasRespuesta:
    # si la fecha de fin es menor que la inicia pues sale error
    if fecha_fin < fecha_inicio:
        raise HTTPException(status_code=422, detail="La fecha final no puede ser anterior a la inicial.")
    # se guarda la resta de la fecha fin - inicio, el resultado devuleve un days y le pones el +1 porque debemos contar el dia inicial y final como tal
    dias_calendario = (fecha_fin - fecha_inicio).days + 1
    # NUMERIC(6,2) admite hasta 9999.99; evitamos intervalos fuera del alcance de la tabla
    if dias_calendario > 9999:
        raise HTTPException(status_code=422, detail="El intervalo no puede superar 9999 días.")
    # fechas únicas: dos registros del mismo feriado no descuentan dos veces
    feriados = await consultar_fechas_feriados(sesion, fecha_inicio, fecha_fin)
    # retornamos la informacion sobre el calculo hecho
    return CalculoDiasRespuesta(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        dias_calendario=dias_calendario,
        feriados_excluidos=feriados,
        dias_vacaciones=Decimal(dias_calendario - len(feriados)),
    )

# funcion para validar los dias de una solicitud usando el calculo anterior
async def calcular_dias_solicitud(sesion: AsyncSession, datos: SolicitudDatos) -> Decimal:
    calculo = await calcular_dias_vacaciones(sesion, datos.fecha_inicio, datos.fecha_fin)
    if calculo.dias_vacaciones <= 0:
        raise HTTPException(status_code=422, detail="El intervalo no contiene días descontables de vacaciones.")
    # compatibilidad: se acepta el valor anterior, pero solo si coincide con el cálculo
    if datos.dias_solicitados is not None and datos.dias_solicitados != calculo.dias_vacaciones:
        raise HTTPException(
            status_code=422,
            detail=f"Los días indicados no coinciden con el cálculo: {calculo.dias_vacaciones} días.",
        )
    return calculo.dias_vacaciones
