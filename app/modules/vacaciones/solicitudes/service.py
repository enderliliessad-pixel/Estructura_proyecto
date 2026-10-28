from datetime import datetime, timezone
from app.modules.vacaciones.reservas.service import reservar_dias, liberar_reservas

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.solicitudes.model import Solicitud
from app.modules.vacaciones.aprobaciones.repository import consultar_aprobaciones_por_solicitud
from app.modules.vacaciones.solicitudes.repository import (
    consultar_solicitudes_por_empleado,
    consultar_solicitud_por_id,
    bloquear_solicitud_y_empleado,
    bloquear_empleado,
    guardar_cambios_solicitud,
    insertar_solicitud,
)
from app.modules.vacaciones.calculos.service import calcular_dias_solicitud
from app.modules.vacaciones.solicitudes.schema import SolicitudRespuesta, SolicitudCrear, SolicitudActualizar

# funcion para obtener las solicitudes y devuelve una lista
async def obtener_solicitudes_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[SolicitudRespuesta]:
    # se guarda la consulta a la base en solicitudes
    solicitudes = await consultar_solicitudes_por_empleado(sesion, id_empleado)
    # el return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
    return [SolicitudRespuesta.model_validate(solicitud) for solicitud in solicitudes]

# funcion para crear una nueva solicitud
async def crear_solicitud(
    sesion: AsyncSession, datos: SolicitudCrear
) -> SolicitudRespuesta:
    try:
        # Confirma al terminar; si ocurre un error, revierte la operación.
        async with sesion.begin():
            # bloqueamos al empleado antes de consultar o reservar sus dias
            await bloquear_empleado(sesion, datos.id_empleado)
            dias = await calcular_dias_solicitud(sesion, datos)
            solicitud = Solicitud(
                **datos.model_dump(exclude={"dias_solicitados"}),
                dias_solicitados=dias,
                estado="PENDIENTE",
                # La columna actual es TIMESTAMP sin zona: guardamos UTC por convenio.
                fecha_solicitud=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            solicitud = await insertar_solicitud(sesion, solicitud)
            await reservar_dias(sesion, solicitud)
            respuesta = SolicitudRespuesta.model_validate(solicitud)
    except IntegrityError as error:
        # La FK protege también si el empleado se elimina durante el registro.
        if getattr(error.orig, "sqlstate", None) == "23503":
            raise HTTPException(
                status_code=409,
                detail="No se pudo registrar la solicitud: verifica que el empleado siga existiendo.",
            ) from None
        raise

    return respuesta

# funcion para obtener una asolicitud en especifico
async def obtener_solicitud_por_id(
    sesion: AsyncSession, id_solicitud: int
) -> SolicitudRespuesta:
    solicitud = await consultar_solicitud_por_id(sesion, id_solicitud)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="La solicitud no existe.")
    return SolicitudRespuesta.model_validate(solicitud)

# funcion para actualizar una solicitud
async def actualizar_solicitud(
    sesion: AsyncSession, id_solicitud: int, datos: SolicitudActualizar
) -> SolicitudRespuesta:
    async with sesion.begin():
        # Comparte el bloqueo utilizado al aprobar o rechazar.
        solicitud = await bloquear_solicitud_y_empleado(sesion, id_solicitud)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="La solicitud no existe.")
        if solicitud.tipo != "VACACIONES":
            raise HTTPException(
                status_code=409, detail="Esta operación solo edita solicitudes de vacaciones."
            )
        if solicitud.estado != "PENDIENTE":
            raise HTTPException(
                status_code=409, detail="Solo se pueden editar solicitudes pendientes."
            )
        decisiones = await consultar_aprobaciones_por_solicitud(sesion, id_solicitud)
        if decisiones:
            raise HTTPException(
                status_code=409, detail="No se puede editar una solicitud con decisiones registradas."
            )

        dias = await calcular_dias_solicitud(sesion, datos)
        # liberamos la reserva anterior; si la nueva falla, la transaccion restaura todo
        await liberar_reservas(sesion, id_solicitud)
        solicitud.fecha_inicio = datos.fecha_inicio
        solicitud.fecha_fin = datos.fecha_fin
        solicitud.dias_solicitados = dias
        solicitud.motivo = datos.motivo
        await reservar_dias(sesion, solicitud)
        solicitud = await guardar_cambios_solicitud(sesion, solicitud)
        respuesta = SolicitudRespuesta.model_validate(solicitud)

    return respuesta


# cancelamos una solicitud pendiente sin eliminar su registro
async def cancelar_solicitud(
    sesion: AsyncSession, id_solicitud: int
) -> SolicitudRespuesta:
    async with sesion.begin():
        # bloqueamos la fila mientras se comprueba y cambia el estado
        solicitud = await bloquear_solicitud_y_empleado(sesion, id_solicitud)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="La solicitud no existe.")
        if solicitud.tipo != "VACACIONES":
            raise HTTPException(
                status_code=409, detail="Esta operación solo cancela solicitudes de vacaciones."
            )
        if solicitud.estado != "PENDIENTE":
            raise HTTPException(
                status_code=409, detail="Solo se pueden cancelar solicitudes pendientes."
            )
        decisiones = await consultar_aprobaciones_por_solicitud(sesion, id_solicitud)
        if decisiones:
            raise HTTPException(
                status_code=409, detail="No se puede cancelar una solicitud con decisiones registradas."
            )

        # liberamos lo apartado sin registrar consumo de dias
        await liberar_reservas(sesion, id_solicitud)
        # conservamos los datos originales; esta operación no modifica saldos
        solicitud.estado = "CANCELADA"
        solicitud = await guardar_cambios_solicitud(sesion, solicitud)
        respuesta = SolicitudRespuesta.model_validate(solicitud)

    return respuesta


# funcion para incorporar una solicitud antigua al nuevo control de reservas
async def conciliar_reserva_solicitud(sesion: AsyncSession, id_solicitud: int) -> SolicitudRespuesta:
    async with sesion.begin():
        solicitud = await bloquear_solicitud_y_empleado(sesion, id_solicitud)
        if solicitud is None:
            raise HTTPException(status_code=404, detail="La solicitud no existe.")
        if solicitud.estado != "PENDIENTE" or solicitud.tipo != "VACACIONES" or solicitud.reserva_gestionada:
            raise HTTPException(status_code=409, detail="Solo se concilian vacaciones pendientes antiguas sin reserva.")
        if await consultar_aprobaciones_por_solicitud(sesion, id_solicitud):
            raise HTTPException(status_code=409, detail="Revisa las decisiones anteriores antes de conciliar.")
        # verificamos que el documento antiguo coincida con sus fechas y el calendario actual
        try:
            datos = SolicitudActualizar(fecha_inicio=solicitud.fecha_inicio, fecha_fin=solicitud.fecha_fin,
                                        dias_solicitados=solicitud.dias_solicitados, motivo=solicitud.motivo)
        except ValidationError:
            raise HTTPException(status_code=409, detail="Completa los datos de la solicitud antigua antes de conciliar.") from None
        if solicitud.dias_solicitados is None:
            raise HTTPException(status_code=409, detail="La solicitud antigua no tiene días registrados.")
        await calcular_dias_solicitud(sesion, datos)
        await reservar_dias(sesion, solicitud, conciliacion=True)
        respuesta = SolicitudRespuesta.model_validate(solicitud)
    return respuesta
