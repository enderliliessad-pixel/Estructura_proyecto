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
        "Los días se ingresan manualmente; todavía no se calculan ni descuentan saldos. "
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

# peticion para consultar el detalle de una solicitud en especifico
@router.get(
    "/detalle/{id_solicitud}",
    response_model=SolicitudRespuesta,
    summary="Consultar una solicitud por su ID",
    responses={404: {"description": "La solicitud no existe."}},
)

# funcion para consultar el detalle de una solicitud en especifico
async def consultar_detalle_solicitud(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> SolicitudRespuesta:
    return await obtener_solicitud_por_id(sesion, id_solicitud)

# pticion para actualizar fechas o motivos
@router.put(
    "/detalle/{id_solicitud}",
    response_model=SolicitudRespuesta,
    summary="Editar fechas, días y motivo de una solicitud pendiente",
    description=(
        "Reemplaza los cuatro campos editables; todos son obligatorios. "
        "Conserva el empleado, el estado, el tipo, las horas y la fecha de registro. "
        "No calcula ni descuenta saldos. Uso local de desarrollo: "
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
# funcion para cancelar una solicitut que aun este pendient.
async def cancelar_solicitud_pendiente(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> SolicitudRespuesta:
    return await cancelar_solicitud(sesion, id_solicitud)
