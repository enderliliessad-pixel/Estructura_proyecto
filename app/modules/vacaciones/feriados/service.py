from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.feriados.repository import consultar_feriados
from app.modules.vacaciones.feriados.schema import FeriadoRespuesta

# funcion asyn para obtener los feriados, va a devolver una lista
# se guardara la consulta en feriado
# El return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
async def obtener_feriados(sesion: AsyncSession) -> list[FeriadoRespuesta]:
    feriados = await consultar_feriados(sesion)
    return [FeriadoRespuesta.model_validate(feriado) for feriado in feriados]
