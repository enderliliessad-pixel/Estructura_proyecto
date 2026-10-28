from datetime import date
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

# funcion para consultar el feriado por el id del mismo
async def consultar_feriado_por_id(
    sesion: AsyncSession, id_feriado: int
) -> Feriado | None:
    consulta = (select(Feriado)
                .where(Feriado.id_feriado == id_feriado))
    return await sesion.scalar(consulta)


# Funcion para consultar un feriado y acualizar
# uso de with_for_update para que no exista cambios simultaneos
async def consultar_feriado_para_actualizar(
    sesion: AsyncSession, id_feriado: int
) -> Feriado | None:
    consulta = (
        select(Feriado)
        .where(Feriado.id_feriado == id_feriado)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return await sesion.scalar(consulta)

# funcion para insertar un nuevo feriado
async def insertar_feriado(sesion: AsyncSession, feriado: Feriado) -> Feriado:
    sesion.add(feriado)
    # enviamos el INSERT a la base y obtenemos el ID generado
    await sesion.flush()
    await sesion.refresh(feriado)
    return feriado

# funcion para guardar cambios hechos en un feriado
async def guardar_cambios_feriado(sesion: AsyncSession, feriado: Feriado) -> Feriado:
    await sesion.flush()
    await sesion.refresh(feriado)
    return feriado

# funcion para consultar las fechas de un feriado
async def consultar_fechas_feriados(
    sesion: AsyncSession, fecha_inicio: date, fecha_fin: date
) -> list[date]:
    consulta = (
        select(Feriado.fecha)
        .where(Feriado.estado.is_(True), Feriado.fecha.between(fecha_inicio, fecha_fin))
        .distinct()
        .order_by(Feriado.fecha)
    )
    resultado = await sesion.scalars(consulta)
    return list(resultado.all())
