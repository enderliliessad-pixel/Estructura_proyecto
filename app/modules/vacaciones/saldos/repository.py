from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.saldos.model import Saldo

# funcion para consultar el saldo y trae una lista
async def consultar_saldos_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[Saldo]:
    # la consulta con la base de datos
    consulta = (
        # seleccionar la tabla saldo
        # donde el id empleado sea igual a id empleado
        # ordenamos el salod por su id de menor a mayor
        select(Saldo)
        .where(Saldo.id_empleado == id_empleado)
        .order_by(Saldo.id_saldo)
    )
    # se guarda en resultado la consulta y se devulve una lista
    resultado = await sesion.scalars(consulta)
    return list(resultado.all())
