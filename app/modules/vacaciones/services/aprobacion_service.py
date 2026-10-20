from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.repositories.aprobacion_repository import (
    consultar_aprobaciones_por_solicitud,
)
from app.modules.vacaciones.schemas.aprobacion_schema import AprobacionRespuesta

# funcion async para obtener las aprobaciones
# obtenemos la sesion, el id y devolvera una lista
async def obtener_aprobaciones_por_solicitud(
    sesion: AsyncSession, id_solicitud: int
) -> list[AprobacionRespuesta]:
# se guardara la consulta en aprobaciones con los datos
# El return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
    aprobaciones = await consultar_aprobaciones_por_solicitud(sesion, id_solicitud)
    return [AprobacionRespuesta.model_validate(aprobacion) for aprobacion in aprobaciones]
