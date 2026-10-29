from sqlalchemy import select, table, column, BigInteger, Boolean, Date
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

# consultamos Core sin modificar la fecha de ingreso ni el estado del empleado
async def consultar_datos_empleado(sesion: AsyncSession, id_empleado: int):
    empleados = table(
        "empleados", column("id_empleado", BigInteger),
        column("fecha_ingreso", Date), column("estado", Boolean), schema="core",
    )
    resultado = await sesion.execute(
        select(empleados.c.fecha_ingreso, empleados.c.estado)
        .where(empleados.c.id_empleado == id_empleado)
    )
    return resultado.mappings().one_or_none()


# guardamos todos los periodos juntos; el servicio confirma la transaccion
async def insertar_periodos(sesion: AsyncSession, saldos: list[Saldo]) -> None:
    sesion.add_all(saldos)
    await sesion.flush()