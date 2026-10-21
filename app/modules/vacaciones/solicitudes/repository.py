from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.solicitudes.model import Solicitud

# funcion para consultar solicitudes y trae una lista
async def consultar_solicitudes_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[Solicitud]:
    # consulta con la base
    consulta = (
        # seleccionar de la tabla solicitud
        # donde el id empleado sea igual a id empleado
        # ordenado por la fecha en forma descendente, los nulos al final
        # si existen 2 solicitudes al mismo tiempo, se va a ordenar por su id de forma descendente
        select(Solicitud)
        .where(Solicitud.id_empleado == id_empleado)
        .order_by(Solicitud.fecha_solicitud.desc().nulls_last(), Solicitud.id_solicitud.desc())
    )
    # se guarda en resultado la consulta y se devulve una lista
    resultado = await sesion.scalars(consulta)
    return list(resultado.all())
