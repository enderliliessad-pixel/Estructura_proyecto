from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.models.aprobacion_model import Aprobacion

# funcion asyn para aceptar varias consultas
# recibe la sesion para conectar con la base y busca la id de la solicitud
async def consultar_aprobaciones_por_solicitud(
    sesion: AsyncSession, id_solicitud: int
    # va a devolver una lista
) -> list[Aprobacion]:
    # como el nombre dice, esta es la consulta con la base, seleccionamos de la tabla aprobaciones
    # donde la id de la solicitud sea igual a la id de la solicitud
    # ordenadas por fecha de mayor a menor, y si son nulos se van al final
    # si existen 2 aprobaciones iguales de tiempo, se ordenaran por su id
    consulta = (
        select(Aprobacion)
        .where(Aprobacion.id_solicitud == id_solicitud)
        .order_by(Aprobacion.fecha.desc().nulls_last(), Aprobacion.id_aprobacion.desc())
    )
    # espera a la consulta con la base y devulve el resultado como lista
    resultado = await sesion.scalars(consulta)
    return list(resultado.all())
