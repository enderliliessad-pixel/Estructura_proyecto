from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.modules.vacaciones.schemas.feriado_schema import FeriadoRespuesta
from app.modules.vacaciones.services.feriado_service import obtener_feriados

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
