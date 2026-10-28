from app.modules.vacaciones.solicitudes.service import conciliar_reserva_solicitud
from app.modules.vacaciones.reservas.service import obtener_historial_reservas
from app.modules.vacaciones.reservas.schema import ReservaRespuesta
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.modules.vacaciones.solicitudes.schema import SolicitudRespuesta, SolicitudActualizar, SolicitudCrear
from app.modules.vacaciones.solicitudes.service import (
    obtener_solicitudes_por_empleado, actualizar_solicitud,
    crear_solicitud,
    cancelar_solicitud,
    obtener_solicitud_por_id,
)

# ruta para conectar con el main y uso de prefix para saber la ruta de este controlador
router = APIRouter(
    prefix="/solicitudes", 
    tags=["Solicitudes"]
)

# solo acepta peticiones de revision, lectura o obtencion de datos.
@router.get(
     # se solicita el id del empleado
    "/{id_empleado}",
    # indicamos que los datos deben tener el formato de la lista
    response_model=list[SolicitudRespuesta],
    # documentacion
    summary="Consultar solicitudes de un trabajador",
    description=(
        "Devuelve las solicitudes registradas, con las más recientes primero. "
        "Si no hay registros, devuelve una lista vacía."
    ),
)

# funcion async para indicar que el empleado tiene ue tener un numero mayor o igual 1 y menor o igual al otro
async def consultar_solicitudes(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    # abrimos una sesion a traves de la funcion y decimos que va a enviar una lista
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[SolicitudRespuesta]:
    # Se pasa el id del empleado y la sesio
    return await obtener_solicitudes_por_empleado(sesion, id_empleado)


# peticions para registrar una solicitud
@router.post(
    "",
    response_model=SolicitudRespuesta,
    status_code=201,
    summary="Registrar una solicitud de vacaciones pendiente",
    description=(
        "Registra vacaciones en días para un empleado existente. "
        "El servidor asigna el estado PENDIENTE y la fecha de registro en UTC. "
        "Los días se calculan incluyendo fines de semana y excluyendo feriados activos. No descuenta saldos. "
        "Uso local de desarrollo: la integración de identidad y roles con Core está pendiente."
    ),
    responses={
        404: {"description": "El empleado no existe."},
        409: {"description": "Conflicto con la referencia al empleado."},
    },
)
# funcion async para registrar la solicitud con los datos
async def registrar_solicitud(
    datos: SolicitudCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
    # devolvera una respuesta a la solicitud
) -> SolicitudRespuesta:
    return await crear_solicitud(sesion, datos)

# peticion para consultar el detalle de una solicitud
@router.get(
    "/detalle/{id_solicitud}",
    response_model=SolicitudRespuesta,
    summary="Consultar una solicitud por su ID",
    responses={404: {"description": "La solicitud no existe."}},
)

# funcion para consultar el detalle de una solicitud
async def consultar_detalle_solicitud(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> SolicitudRespuesta:
    return await obtener_solicitud_por_id(sesion, id_solicitud)

# peticion para actualizar fechas o motivos
@router.put(
    "/detalle/{id_solicitud}",
    response_model=SolicitudRespuesta,
    summary="Editar fechas, días y motivo de una solicitud pendiente",
    description=(
        "Reemplaza fechas y motivo; los días se calculan. Si se envían días, deben coincidir. "
        "Conserva el empleado, el estado, el tipo, las horas y la fecha de registro. "
        "No descuenta saldos. Uso local de desarrollo: "
        "la autenticación y la autorización por propietario o rol de Core están pendientes."
    ),
    responses={
        404: {"description": "La solicitud no existe."},
        409: {"description": "La solicitud no admite edición."},
    },
)
# funcion para editar la solicitud
async def editar_solicitud(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: SolicitudActualizar,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> SolicitudRespuesta:
    return await actualizar_solicitud(sesion, id_solicitud, datos)


# peticion para cancelar una solicitud sin borrar su historial
@router.patch(
    "/detalle/{id_solicitud}/cancelar",
    response_model=SolicitudRespuesta,
    summary="Cancelar una solicitud de vacaciones pendiente",
    description=(
        "Cambia el estado a CANCELADA si la solicitud está PENDIENTE y no tiene decisiones. "
        "Conserva el registro y no modifica saldos. No requiere cuerpo de petición. "
        "Uso local de desarrollo: la autenticación y la autorización por propietario "
        "o rol de Core están pendientes."
    ),
    responses={
        404: {"description": "La solicitud no existe."},
        409: {"description": "La solicitud no admite cancelación."},
    },
)
async def cancelar_solicitud_pendiente(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> SolicitudRespuesta:
    return await cancelar_solicitud(sesion, id_solicitud)

# ruta para consultar el historial de reservas sin modificarlo
@router.get("/detalle/{id_solicitud}/reservas", response_model=list[ReservaRespuesta])
async def consultar_historial_reservas(id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
                                     sesion: Annotated[AsyncSession, Depends(obtener_sesion)]):
    return await obtener_historial_reservas(sesion, id_solicitud)

# ruta para incorporar pendientes antiguos despues de revisar su documento
@router.post("/detalle/{id_solicitud}/reserva", response_model=SolicitudRespuesta,
             summary="Conciliar la reserva de una solicitud pendiente antigua")
async def conciliar_reserva(id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
                           sesion: Annotated[AsyncSession, Depends(obtener_sesion)]):
    return await conciliar_reserva_solicitud(sesion, id_solicitud)
