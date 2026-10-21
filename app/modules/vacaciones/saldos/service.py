from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.saldos.repository import (
    consultar_saldos_por_empleado,
)
from app.modules.vacaciones.saldos.schema import SaldoRespuesta

# funcion async para obtener los saldos y devuelve una lista
async def obtener_saldos_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[SaldoRespuesta]:
    # la consulta se guarda en saldo
    saldos = await consultar_saldos_por_empleado(sesion, id_empleado)
    # el return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
    return [SaldoRespuesta.model_validate(saldo) for saldo in saldos]
