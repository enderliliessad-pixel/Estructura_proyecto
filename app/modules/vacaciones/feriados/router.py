from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.modules.vacaciones.feriados.schema import (
    FeriadoRespuesta, FeriadoCrear, FeriadoActualizar, FeriadoEstado,
)
from app.modules.vacaciones.feriados.service import (
    obtener_feriados,
    obtener_feriado_por_id,
    crear_feriado,
    actualizar_feriado,
    cambiar_estado_feriado,
)

# ruta para conectar con el main y uso de prefix para saber la ruta de este controlador
router = APIRouter(
    prefix="/feriados",
    tags=["Feriados"]
)

# solo acepta peticiones de revision, lectura o obtencion de datos
@router.get(
    # colocamos comillas porque los feriados son de toda la empresa y no de cada usuario
    "",
    # response para indicar que la lista que obtenga tiene que tener el formato establecido
    response_model=list[FeriadoRespuesta],
    # documentacion de fast api
    summary="Consultar feriados registrados",
    description=(
        "Devuelve todos los feriados registrados, incluidos los inactivos, "
        "ordenados por fecha. Cada registro incluye su estado."
    ),
)
# funcion asyn para obtener una sesion temporal y list para indicar que se va a retornar una lista con el siguiente formato
async def listar_feriados(
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[FeriadoRespuesta]:
    return await obtener_feriados(sesion)

# Documentacion para ver un feriado por su id 
@router.get(
    "/{id_feriado}",
    response_model=FeriadoRespuesta,
    summary="Consultar un feriado por su ID",
    responses={404: {"description": "El feriado no existe."}},
)
# funcion async para consultar el detalle de feriado
async def consultar_detalle_feriado(
    id_feriado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> FeriadoRespuesta:
    return await obtener_feriado_por_id(sesion, id_feriado)

# Documentacion para regitrar un feriado
@router.post(
    "",
    response_model=FeriadoRespuesta,
    status_code=201,
    summary="Registrar un feriado",
    description=(
        "Registra fecha, descripción y tipo. El estado predeterminado es activo. "
        "No calcula ni modifica saldos o solicitudes. "
        "Uso local de desarrollo: autenticación y permisos de administración pendientes de Core."
    ),
)
# funcion para registrar un nuevo feriado
async def registrar_feriado(
    datos: FeriadoCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> FeriadoRespuesta:
    return await crear_feriado(sesion, datos)

# Documentacion para editar un feriado
@router.put(
    "/{id_feriado}",
    response_model=FeriadoRespuesta,
    summary="Editar fecha, descripción y tipo de un feriado",
    description=(
        "Los tres campos son obligatorios. Conserva el estado actual. "
        "No recalcula solicitudes ni saldos. "
        "Uso local de desarrollo: autenticación y permisos de administración pendientes de Core."
    ),
    responses={404: {"description": "El feriado no existe."}},
)
# funcion para editar un feriado
async def editar_feriado(
    id_feriado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: FeriadoActualizar,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> FeriadoRespuesta:
    return await actualizar_feriado(sesion, id_feriado, datos)

# Documentacion para ver un activar un feriado o no
@router.patch(
    "/{id_feriado}/estado",
    response_model=FeriadoRespuesta,
    summary="Activar o desactivar un feriado",
    description=(
        "Acepta estado true o false. Conserva el registro y sus demás campos. "
        "No recalcula solicitudes ni saldos. "
        "Uso local de desarrollo: autenticación y permisos de administración pendientes de Core."
    ),
    responses={404: {"description": "El feriado no existe."}},
)
# funcion para modificar el estado de un feriado
async def modificar_estado_feriado(
    id_feriado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: FeriadoEstado,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> FeriadoRespuesta:
    return await cambiar_estado_feriado(sesion, id_feriado, datos)
