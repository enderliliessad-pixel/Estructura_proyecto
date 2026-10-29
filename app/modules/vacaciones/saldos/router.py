from datetime import date
from app.modules.vacaciones.saldos.schema import ResumenSaldoRespuesta, PrevisionRespuesta
from app.modules.vacaciones.saldos.service import obtener_resumen_saldo, prever_descuentos

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_sesion
from app.modules.vacaciones.saldos.schema import SaldoRespuesta
from app.modules.vacaciones.saldos.service import obtener_saldos_por_empleado
from app.modules.vacaciones.saldos.schema import GeneracionPeriodosCrear, GeneracionPeriodosRespuesta
from app.modules.vacaciones.saldos.service import generar_periodos

# ruta para conectar con el main y uso de prefix para saber la ruta de este controlador
router = APIRouter(
    prefix="/saldos", 
    tags=["Saldos"]
)

# solo acepta peticiones de revision, lectura o obtencion de datos.
@router.get(
    # se solicita el id del empleado
    "/{id_empleado}",
    # indicamos que los datos deben tener el formato de la lista
    response_model=list[SaldoRespuesta],
    # documentacion
    summary="Consultar saldos de un trabajador",
    description=(
        "Devuelve los saldos registrados del trabajador. "
        "Si no tiene registros, devuelve una lista vacía."
    ),
)
# funcion async para indicar que el empleado tiene ue tener un numero mayor o igual 1 y menor o igual al otro
async def consultar_saldos(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    # abrimos una sesion a traves de la funcion y decimos que va a enviar una lista
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[SaldoRespuesta]:
    # Se pasa el id del empleado y la sesion
    return await obtener_saldos_por_empleado(sesion, id_empleado)

# documentacion para consultar saldo
@router.get(
    "/{id_empleado}/resumen", response_model=ResumenSaldoRespuesta,
    summary="Consultar saldos por período y total acreditado",
    description="Suma únicamente saldos ya acreditados. Requiere fechas y cantidades completas y consistentes.",
    responses={404: {"description": "El empleado no existe."}, 409: {"description": "Revisar los datos de los saldos."}},
)
# funcion para consultar el resumen de saldo
async def consultar_resumen_saldo(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> ResumenSaldoRespuesta:
    return await obtener_resumen_saldo(sesion, id_empleado)

# documentacion para consultar prevision de saldo
@router.get(
    "/{id_empleado}/prevision", response_model=PrevisionRespuesta,
    summary="Prever el descuento desde los períodos más antiguos",
    description=(
        "Solo consulta: no aprueba, no reserva y no modifica saldos. Usa días acreditados hoy, "
        "aunque la solicitud sea futura. El faltante no autoriza vacaciones anticipadas. "
        "fecha_fin es el último día de ausencia. Identidad y roles pendientes de Core."
    ),
    responses={404: {"description": "El empleado no existe."}, 409: {"description": "Revisar los datos de los saldos."}},
)

# funcion para consultar prevision
async def consultar_prevision(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    fecha_inicio: date, fecha_fin: date,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> PrevisionRespuesta:
    return await prever_descuentos(sesion, id_empleado, fecha_inicio, fecha_fin)

# ruta para generar periodos sin volver a asignar los dias de saldos ya existentes
@router.post(
    "/{id_empleado}/periodos", response_model=GeneracionPeriodosRespuesta,
    summary="Generar períodos y asignar días por antigüedad",
    description=(
        "Operación local de Talento Humano; identidad autenticada pendiente de Core. "
        "Crea los períodos faltantes hasta el que está en curso y conserva los existentes. "
        "Sin fecha_desde continúa desde el último período iniciado registrado; si no hay saldos, "
        "crea solo el actual. Para recuperar períodos anteriores indica su fecha inicial, "
        "tras revisar que no representen vacaciones ya disfrutadas. No se ejecuta en segundo plano."
    ),
    responses={403: {"description": "Responsable no habilitado."},
               404: {"description": "El empleado no existe."},
               409: {"description": "Revisar empleado o saldos existentes."}},
)
async def registrar_periodos(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: GeneracionPeriodosCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> GeneracionPeriodosRespuesta:
    return await generar_periodos(sesion, id_empleado, datos)
