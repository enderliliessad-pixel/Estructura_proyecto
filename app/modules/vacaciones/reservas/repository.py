from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.vacaciones.reservas.model import Reserva
from app.modules.vacaciones.saldos.model import Saldo

# funcion para bloquear los saldos siempre en el mismo orden y evitar bloqueos cruzados
async def bloquear_saldos(sesion: AsyncSession, id_empleado: int) -> list[Saldo]:
    # consulta que indica que los saldos por su id se coloquen en orden y con with_for_update para bloquear y que no siga hasta que otro proceso termine
    consulta = (select(Saldo).where(Saldo.id_empleado == id_empleado)
                .order_by(Saldo.id_saldo).with_for_update()
                .execution_options(populate_existing=True))
    return list((await sesion.scalars(consulta)).all())

# funcion para consultar las reservas de una solicitud, incluyendo su historial
async def consultar_reservas(sesion: AsyncSession, id_solicitud: int) -> list[Reserva]:
    consulta = select(Reserva).where(Reserva.id_solicitud == id_solicitud).order_by(Reserva.id_reserva)
    return list((await sesion.scalars(consulta)).all())

# funcion para consultar todo lo que sigue apartado para el trabajador
async def consultar_reservas_activas(sesion: AsyncSession, id_empleado: int) -> list[Reserva]:
    consulta = select(Reserva).where(Reserva.id_empleado == id_empleado, Reserva.estado == "ACTIVA")
    return list((await sesion.scalars(consulta)).all())
