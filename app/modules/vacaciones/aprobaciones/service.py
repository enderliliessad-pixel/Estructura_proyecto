from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.aprobaciones.repository import (
    consultar_aprobaciones_por_solicitud,
    existe_aprobador,
    insertar_aprobacion,
)
from app.modules.vacaciones.aprobaciones.schema import AprobacionRespuesta, RechazoCrear
from app.modules.vacaciones.aprobaciones.model import Aprobacion
from app.modules.vacaciones.solicitudes.repository import (
    consultar_solicitud_para_actualizar,
    guardar_cambios_solicitud,
)

# funcion async para obtener las aprobaciones
# obtenemos la sesion, el id y devolvera una lista
async def obtener_aprobaciones_por_solicitud(
    sesion: AsyncSession, id_solicitud: int
) -> list[AprobacionRespuesta]:
# se guardara la consulta en aprobaciones con los datos
# El return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
    aprobaciones = await consultar_aprobaciones_por_solicitud(sesion, id_solicitud)
    return [AprobacionRespuesta.model_validate(aprobacion) for aprobacion in aprobaciones]


# registramos la decisión y cambiamos el estado como una sola operación
async def rechazar_solicitud(
    sesion: AsyncSession, id_solicitud: int, datos: RechazoCrear
) -> AprobacionRespuesta:
    # realizamos un try para capturar diferentes errores
    try:
        # iniciamos una transaccion para guardar la decision y el estado juntos
        # si ocurre un error se revierten los cambios, caso contrario se confirman
        async with sesion.begin():
            # consultamos la solicitud y bloqueamos la fila hasta que se realize el cambio
            solicitud = await consultar_solicitud_para_actualizar(sesion, id_solicitud)
            if solicitud is None:
                raise HTTPException(status_code=404, detail="La solicitud no existe.")
            if solicitud.tipo != "VACACIONES":
                raise HTTPException(
                    status_code=409, detail="Esta operación solo rechaza solicitudes de vacaciones."
                )
            if solicitud.estado != "PENDIENTE":
                raise HTTPException(
                    status_code=409, detail="Solo se pueden rechazar solicitudes pendientes."
                )
            # seccion para indicar que una solicitud tiene una decision activa
            decisiones = await consultar_aprobaciones_por_solicitud(sesion, id_solicitud)
            if decisiones:
                raise HTTPException(
                    status_code=409, detail="La solicitud ya tiene decisiones registradas."
                )
            if not await existe_aprobador(sesion, datos.id_aprobador):
                raise HTTPException(status_code=404, detail="El empleado aprobador no existe.")
            
            # Se va a crear el registro del motivo de aprobacion o negracion de la solicitud con los datos del aprobador
            aprobacion = Aprobacion(
                id_solicitud=id_solicitud,
                id_aprobador=datos.id_aprobador,
                decision="RECHAZADA",
                observacion=datos.observacion,
                # obtenemos la fecha y hora actual en UTC
                # quitamos la informacion de zona porque la columna es TIMESTAMP sin zona
                # esto conserva la hora UTC, no la convierte a la hora de Ecuador
                fecha=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            # se cambia el estado de la solicitud
            solicitud.estado = "RECHAZADA"
            # se inserta la aprobacion y se espera para guardar los cambios
            aprobacion = await insertar_aprobacion(sesion, aprobacion)
            await guardar_cambios_solicitud(sesion, solicitud)
            respuesta = AprobacionRespuesta.model_validate(aprobacion)
            # capturamos errores relacionados con las restricciones de la base de datos
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23503":
            raise HTTPException(
                status_code=409,
                detail="No se pudo registrar el rechazo: verifica que la solicitud y el aprobador sigan existiendo.",
            ) from None
        raise

    return respuesta
