from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.modules.diagnostico.schema import EstadoRespuesta
from app.modules.diagnostico.service import comprobar_base_datos

# seccion para conocer si la conexion con la base es estable
router = APIRouter(
    tags=["Diagnóstico local"]
    )

# esta seccion solo sirve para indicar que la conexion con la base responde peticiones
@router.get("/estado", response_model=EstadoRespuesta)
async def estado():
    respuesta=EstadoRespuesta(mensaje="API de vacaciones en funcionamiento.")
    return respuesta

# es una capa mas de seguridad para verificar que la base esta respondiendo correctamente
@router.get("/estado/bd", response_model=EstadoRespuesta)
async def estado_base_datos(sesion: AsyncSession = Depends(obtener_sesion)):
    try:
        disponible = await comprobar_base_datos(sesion)
    except (SQLAlchemyError, OSError, TimeoutError):
        raise HTTPException( status_code=503, detail="No se pudo conectar con PostgreSQL. Revisa la configuración local.",) from None
    if not disponible:
        raise HTTPException(status_code=503, detail="PostgreSQL no respondió correctamente.")
    return EstadoRespuesta(mensaje="Conexión con PostgreSQL correcta.")

