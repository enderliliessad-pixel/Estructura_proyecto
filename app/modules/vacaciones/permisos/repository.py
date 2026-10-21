from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.permisos.model import Permiso

# funcion para consultar los permisos, y traera una lista
async def consultar_permisos_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[Permiso]:
    # consulta a la base de datos
    consulta = (
        # seleccionar la tabla permisos
        # donde el id del empleado sea igual al id empleado
        # y se ordena de forma descendente, los nulos al final
        # si existen 2 permisos al mismo tiempo, ordena de forma descendente
        select(Permiso)
        .where(Permiso.id_empleado == id_empleado)
        .order_by(Permiso.fecha.desc().nulls_last(), Permiso.id_permiso.desc())
    )
    # se guarda en respuesta la consulta y se devulve una lista
    resultado = await sesion.scalars(consulta)
    return list(resultado.all())
