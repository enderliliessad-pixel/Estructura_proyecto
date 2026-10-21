from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.feriados.model import Feriado

# funcion para indicar que se conectara con la base y devolvera una lista
async def consultar_feriados(sesion: AsyncSession) -> list[Feriado]:
    # consulta de la base
    consulta =(
        # de la tabla feriado
        # ordenar por las fechas de forma ascendente y los nullos al final
        # si 2 feriados caen en la misma fecha los ordeno de menor a mayor
        select(Feriado)
        .order_by(Feriado.fecha.asc().nulls_last(), Feriado.id_feriado)
    ) 
    # se guarda en resultado la consulta y se devuelve una lista
    resultado = await sesion.scalars(consulta)
    return list(resultado.all())
