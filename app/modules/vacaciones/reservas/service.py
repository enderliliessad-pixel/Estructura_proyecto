from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.vacaciones.reservas.model import Reserva, Descuento
from app.modules.vacaciones.reservas.repository import bloquear_saldos, consultar_reservas
from app.modules.vacaciones.solicitudes.repository import consultar_cruce, consultar_pendiente_sin_reserva
from app.modules.vacaciones.saldos.service import obtener_resumen_saldo, distribuir_dias

# funcion para comprobar fechas y pendientes antiguos antes de apartar nuevos dias
async def validar_solicitud_reservable(sesion, solicitud, conciliacion=False):
    cruce = await consultar_cruce(sesion, solicitud.id_empleado, solicitud.fecha_inicio,
                                  solicitud.fecha_fin, solicitud.id_solicitud)
    if cruce is not None:
        raise HTTPException(status_code=409, detail=f"Las fechas se cruzan con la solicitud {cruce}.")
    # la conciliacion procesa un registro a la vez; las altas normales esperan a que termine
    if not conciliacion:
        pendiente = await consultar_pendiente_sin_reserva(sesion, solicitud.id_empleado, solicitud.id_solicitud)
        if pendiente is not None:
            raise HTTPException(status_code=409, detail=f"Concilia primero la reserva de la solicitud antigua {pendiente}.")

# funcion para reservar los dias sin modificar las cantidades utilizadas del saldo
# el servicio que llama esta funcion ya mantiene bloqueado al empleado
async def reservar_dias(sesion: AsyncSession, solicitud, conciliacion=False) -> None:
    await validar_solicitud_reservable(sesion, solicitud, conciliacion)
    await bloquear_saldos(sesion, solicitud.id_empleado)
    resumen = await obtener_resumen_saldo(sesion, solicitud.id_empleado)
    descuentos, faltan = distribuir_dias(resumen, solicitud.dias_solicitados)
    if faltan > 0:
        raise HTTPException(status_code=409, detail=f"Saldo insuficiente: faltan {faltan} días, incluyendo el anticipo permitido.")
    # si se usa saldo anterior al ultimo periodo acreditado, el disfrute se limita a 20 dias
    ultimo = resumen.periodos_acreditados[-1].id_saldo if resumen.periodos_acreditados else None
    antiguos = {s.id_saldo for s in resumen.periodos_acreditados if s.id_saldo != ultimo}
    if solicitud.dias_solicitados > 20 and any(d.id_saldo in antiguos for d in descuentos):
        raise HTTPException(status_code=422, detail="Una solicitud que utiliza vacaciones acumuladas no puede superar 20 días.")
    ahora = datetime.now(timezone.utc)
    for descuento in descuentos:
        sesion.add(Reserva(
            id_empleado=solicitud.id_empleado, id_solicitud=solicitud.id_solicitud,
            id_saldo=descuento.id_saldo, dias_reservados=descuento.dias_a_descontar,
            es_anticipo=descuento.es_anticipo, estado="ACTIVA", fecha_registro=ahora,
        ))
    solicitud.reserva_gestionada = True
    await sesion.flush()

# funcion para liberar la reserva al rechazar, cancelar o editar, conservando su historial
async def liberar_reservas(sesion: AsyncSession, id_solicitud: int) -> None:
    for reserva in await consultar_reservas(sesion, id_solicitud):
        if reserva.estado == "ACTIVA":
            reserva.estado = "LIBERADA"
            reserva.fecha_cierre = datetime.now(timezone.utc)
    await sesion.flush()

# funcion para convertir la reserva en descuento una sola vez dentro de la aprobacion
async def descontar_reservas(sesion: AsyncSession, solicitud) -> None:
    if not solicitud.reserva_gestionada:
        raise HTTPException(status_code=409, detail="Concilia la reserva de esta solicitud antigua antes de aprobarla.")
    saldos = {s.id_saldo: s for s in await bloquear_saldos(sesion, solicitud.id_empleado)}
    # verifica que las reservas de todos los pendientes sigan respaldadas por saldo
    await obtener_resumen_saldo(sesion, solicitud.id_empleado)
    reservas = [r for r in await consultar_reservas(sesion, solicitud.id_solicitud) if r.estado == "ACTIVA"]
    total = sum((r.dias_reservados for r in reservas), Decimal("0.00"))
    if not reservas or total != solicitud.dias_solicitados:
        raise HTTPException(status_code=409, detail="La reserva no coincide con los días de la solicitud.")
    ahora = datetime.now(timezone.utc)
    for reserva in reservas:
        saldo = saldos.get(reserva.id_saldo)
        if saldo is None or saldo.dias_disponibles < reserva.dias_reservados:
            raise HTTPException(status_code=409, detail="El saldo reservado ya no está disponible. Revisa los ajustes manuales.")
        saldo.dias_utilizados += reserva.dias_reservados
        saldo.dias_disponibles -= reserva.dias_reservados
        sesion.add(Descuento(
            id_empleado=solicitud.id_empleado, id_solicitud=solicitud.id_solicitud,
            id_saldo=saldo.id_saldo, dias_descontados=reserva.dias_reservados,
            es_anticipo=reserva.es_anticipo, fecha_registro=ahora,
        ))
        reserva.estado = "CONSUMIDA"
        reserva.fecha_cierre = ahora
    await sesion.flush()


# funcion para consultar las reservas y devolver los esquemas de respuesta
async def obtener_historial_reservas(sesion: AsyncSession, id_solicitud: int):
    from app.modules.vacaciones.solicitudes.repository import consultar_solicitud_por_id
    from app.modules.vacaciones.reservas.schema import ReservaRespuesta
    if await consultar_solicitud_por_id(sesion, id_solicitud) is None:
        raise HTTPException(status_code=404, detail="La solicitud no existe.")
    return [ReservaRespuesta.model_validate(r) for r in await consultar_reservas(sesion, id_solicitud)]
