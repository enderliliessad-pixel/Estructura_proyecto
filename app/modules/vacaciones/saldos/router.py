from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.modules.vacaciones.saldos.schema import SaldoRespuesta
from app.modules.vacaciones.saldos.service import obtener_saldos_por_empleado

# ruta para conectar con el main y uso de prefix para saber la ruta de este controlador
router = APIRouter(
    prefix="/saldos", 
    tags=["Saldos"]
)

# solo acepta peticiones de revision, lectura o obtencion de datos.
@router.get(
    # se solicita el id del empleado
    "/{id_empleado}",
    # indicamos que los datos deben tener el formato de la lista
    response_model=list[SaldoRespuesta],
    # documentacion
    summary="Consultar saldos de un trabajador",
    description=(
        "Devuelve los saldos registrados del trabajador. "
        "Si no tiene registros, devuelve una lista vacía."
    ),
)
# funcion async para indicar que el empleado tiene ue tener un numero mayor o igual 1 y menor o igual al otro
async def consultar_saldos(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    # abrimos una sesion a traves de la funcion y decimos que va a enviar una lista
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[SaldoRespuesta]:
    # Se pasa el id del empleado y la sesion
    return await obtener_saldos_por_empleado(sesion, id_empleado)
