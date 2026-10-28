from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.feriados.model import Feriado
from app.modules.vacaciones.feriados.repository import (
    consultar_feriados,
    consultar_feriado_por_id,
    consultar_feriado_para_actualizar,
    insertar_feriado,
    guardar_cambios_feriado,
)
from app.modules.vacaciones.feriados.schema import (
    FeriadoRespuesta, FeriadoCrear, FeriadoActualizar, FeriadoEstado,
)

# funcion asyn para obtener los feriados, va a devolver una lista
# se guardara la consulta en feriado
# El return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
async def obtener_feriados(sesion: AsyncSession) -> list[FeriadoRespuesta]:
    feriados = await consultar_feriados(sesion)
    return [FeriadoRespuesta.model_validate(feriado) for feriado in feriados]

# funcion para obtener el feriado por su id
async def obtener_feriado_por_id(
    sesion: AsyncSession, id_feriado: int
) -> FeriadoRespuesta:
    feriado = await consultar_feriado_por_id(sesion, id_feriado)
    if feriado is None:
        raise HTTPException(status_code=404, detail="El feriado no existe.")
    return FeriadoRespuesta.model_validate(feriado)

# funcion para crear un feriado
async def crear_feriado(sesion: AsyncSession, datos: FeriadoCrear) -> FeriadoRespuesta:
    async with sesion.begin():
        feriado = Feriado(**datos.model_dump())
        feriado = await insertar_feriado(sesion, feriado)
        respuesta = FeriadoRespuesta.model_validate(feriado)
    return respuesta

# funcion para actualizar un feriado
async def actualizar_feriado(
    sesion: AsyncSession, id_feriado: int, datos: FeriadoActualizar
) -> FeriadoRespuesta:
    async with sesion.begin():
        feriado = await consultar_feriado_para_actualizar(sesion, id_feriado)
        if feriado is None:
            raise HTTPException(status_code=404, detail="El feriado no existe.")

        feriado.fecha = datos.fecha
        feriado.descripcion = datos.descripcion
        feriado.tipo = datos.tipo
        feriado = await guardar_cambios_feriado(sesion, feriado)
        respuesta = FeriadoRespuesta.model_validate(feriado)
    return respuesta

# funcion para cambiar el estado de un feriado
async def cambiar_estado_feriado(
    sesion: AsyncSession, id_feriado: int, datos: FeriadoEstado
) -> FeriadoRespuesta:
    async with sesion.begin():
        feriado = await consultar_feriado_para_actualizar(sesion, id_feriado)
        if feriado is None:
            raise HTTPException(status_code=404, detail="El feriado no existe.")

        # desactivar conserva el registro; repetir el mismo estado es válido
        feriado.estado = datos.estado
        feriado = await guardar_cambios_feriado(sesion, feriado)
        respuesta = FeriadoRespuesta.model_validate(feriado)
    return respuesta
