from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.modules.vacaciones.schemas.permiso_schema import PermisoRespuesta
from app.modules.vacaciones.services.permiso_service import obtener_permisos_por_empleado

# ruta para conectar con el main y uso de prefix para saber la ruta de este controlador
router = APIRouter(
    prefix="/permisos", 
    tags=["Permisos por horas"]
)

# solo acepta peticiones de revision, lectura o obtencion de datos.
@router.get(
    # solicitamos el id del empleado
    "/{id_empleado}",
    # indicamos que los datos deben tener el formato de la lista
    response_model=list[PermisoRespuesta],
    # documentacion
    summary="Consultar permisos por horas de un trabajador",
    description=(
        "Devuelve los permisos registrados, con las fechas más recientes primero. "
        "Esta consulta no calcula ni descuenta días de vacaciones."
    ),
)
# funcion async para indicar que el empleado tiene ue tener un numero mayor o igual 1 y menor o igual al otro
async def consultar_permisos(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    # abrimos una sesion a traves de la funcion y decimos que va a enviar una lista
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[PermisoRespuesta]:
    # Se pasa el id del empleado y la sesion
    return await obtener_permisos_por_empleado(sesion, id_empleado)
