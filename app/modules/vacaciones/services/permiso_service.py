from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.repositories.permiso_repository import (
    consultar_permisos_por_empleado,
)
from app.modules.vacaciones.schemas.permiso_schema import PermisoRespuesta

# funcion para obtener los permisos, devolvera una lista
async def obtener_permisos_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[PermisoRespuesta]:
    # la consulta se guardara en permisos
    permisos = await consultar_permisos_por_empleado(sesion, id_empleado)
    # el return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
    return [PermisoRespuesta.model_validate(permiso) for permiso in permisos]
