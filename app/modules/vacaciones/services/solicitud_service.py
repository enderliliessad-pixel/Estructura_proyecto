from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.repositories.solicitud_repository import (
    consultar_solicitudes_por_empleado,
)
from app.modules.vacaciones.schemas.solicitud_schema import SolicitudRespuesta

# funcion para obtener las solicitudes y devuelve una lista
async def obtener_solicitudes_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[SolicitudRespuesta]:
    # se guarda la consulta a la base en solicitudes
    solicitudes = await consultar_solicitudes_por_empleado(sesion, id_empleado)
    # el return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
    return [SolicitudRespuesta.model_validate(solicitud) for solicitud in solicitudes]
