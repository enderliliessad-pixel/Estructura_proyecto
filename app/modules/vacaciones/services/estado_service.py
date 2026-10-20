from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.repositories.diagnostico_repository import verificar_conexion
# esta funcion existe solo por cuestiones de arquitectura(el repo nunca habla directamente con el controlador)
# funcion async que comprueba la base de datos, y devuelve un booleano
async def comprobar_base_datos(sesion: AsyncSession) -> bool:
    # retornara la verificacion_conexion
    return await verificar_conexion(sesion)

