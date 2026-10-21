from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# funcion para verificar la conexion con la base, va a devolver un booleano
async def verificar_conexion(sesion: AsyncSession) -> bool:
    # se va a enviar un texto para que la base responda 1, si el resultado es igual a 1 la conexion esta bien
    resultado = await sesion.execute(text("SELECT 1"))
    return resultado.scalar_one() == 1

