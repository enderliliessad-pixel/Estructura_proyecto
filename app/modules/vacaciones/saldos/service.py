# usamos el día local del instituto, no la zona horaria del servidor
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.vacaciones.solicitudes.repository import existe_empleado
from app.modules.vacaciones.calculos.service import calcular_dias_vacaciones
from app.modules.vacaciones.saldos.schema import (
    ResumenSaldoRespuesta, DescuentoPrevisto, PrevisionRespuesta,
)


from app.modules.vacaciones.saldos.repository import (
    consultar_saldos_por_empleado,
)
from app.modules.vacaciones.saldos.schema import SaldoRespuesta

# funcion async para obtener los saldos y devuelve una lista
async def obtener_saldos_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[SaldoRespuesta]:
    # la consulta se guarda en saldo
    saldos = await consultar_saldos_por_empleado(sesion, id_empleado)
    # el return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
    return [SaldoRespuesta.model_validate(saldo) for saldo in saldos]

# funcion para obtener la fecha de ecuador
def fecha_actual() -> date:
    return datetime.now(ZoneInfo("America/Guayaquil")).date()

# funcion para obtener los saldos y resumir los dias que un empleado tiene libre
async def obtener_resumen_saldo(sesion: AsyncSession, id_empleado: int) -> ResumenSaldoRespuesta:
    if not await existe_empleado(sesion, id_empleado):
        raise HTTPException(status_code=404, detail="El empleado no existe.")
    # consultamos los saldos del empleado y los guardamos en una lista
    saldos = await consultar_saldos_por_empleado(sesion, id_empleado)
    # recorremos cada saldo para comprobar sus fechas y cantidades
    for saldo in saldos:
        fechas = (saldo.fecha_inicio_periodo, saldo.fecha_fin_periodo, saldo.fecha_acreditacion)
        cantidades = (saldo.dias_asignados, saldo.dias_utilizados, saldo.dias_disponibles)
        if any(fecha is None for fecha in fechas):
            raise HTTPException(status_code=409, detail=f"Completa las fechas del saldo {saldo.id_saldo} antes de calcular su disponibilidad.")
        if saldo.fecha_fin_periodo < saldo.fecha_inicio_periodo:
            raise HTTPException(status_code=409, detail=f"Las fechas del saldo {saldo.id_saldo} son inconsistentes.")
        if any(n is None or not n.is_finite() or n < 0 for n in cantidades):
            raise HTTPException(status_code=409, detail=f"El saldo {saldo.id_saldo} contiene cantidades incompletas, negativas o inválidas. Los anticipos están pendientes de definición.")
        if saldo.dias_asignados - saldo.dias_utilizados != saldo.dias_disponibles:
            raise HTTPException(status_code=409, detail=f"Revisa las cantidades del saldo {saldo.id_saldo}: asignados menos utilizados debe coincidir con disponibles.")
    # ordenamos la lista desde el periodo mas antiguo al mas reciente
    # lambda indica que se use la fecha de inicio y, si coincide, el id del saldo
    saldos.sort(key=lambda s: (s.fecha_inicio_periodo, s.id_saldo))
    # saldos[1:] obtiene la lista desde el segundo elemento
    # zip permite comparar cada saldo con el que viene inmediatamente despues
    for anterior, siguiente in zip(saldos, saldos[1:]):
        # si el siguiente empieza antes o el mismo dia que termina el anterior
        # los periodos comparten fechas y no se permite continuar
        if siguiente.fecha_inicio_periodo <= anterior.fecha_fin_periodo:
            raise HTTPException(status_code=409, detail="Hay períodos de saldo superpuestos. Revisa sus fechas antes de distribuir los días.")
    # obtenemos la fecha actual para comprobar cuales periodos ya estan acreditados
    hoy = fecha_actual()
    # creamos una lista con los saldos cuya acreditacion ya llego o corresponde a hoy
    acreditados = [s for s in saldos if s.fecha_acreditacion <= hoy]
    # creamos una lista con los saldos cuya acreditacion aun no llega
    futuros = [s for s in saldos if s.fecha_acreditacion > hoy]
    # devolvemos el resumen con los periodos separados y el total que puede utilizar
    return ResumenSaldoRespuesta(
        id_empleado=id_empleado, fecha_consulta=hoy,
        # sumamos solamente los dias disponibles de los periodos acreditados
        # iniciamos con Decimal("0.00") para mantener el tipo decimal incluso si no hay saldos
        total_disponible=sum((s.dias_disponibles for s in acreditados), Decimal("0.00")),
        periodos_acreditados=[SaldoRespuesta.model_validate(s) for s in acreditados],
        periodos_no_acreditados=[SaldoRespuesta.model_validate(s) for s in futuros],
    )

# funcion para prever de que periodos se tomarian los dias solicitados
# solo calcula y consulta, no guarda descuentos ni modifica los saldos
async def prever_descuentos(
    sesion: AsyncSession, id_empleado: int, fecha_inicio: date, fecha_fin: date
) -> PrevisionRespuesta:
    calculo = await calcular_dias_vacaciones(sesion, fecha_inicio, fecha_fin)
    resumen = await obtener_resumen_saldo(sesion, id_empleado)
    faltan = calculo.dias_vacaciones
    # creamos una lista vacia donde guardaremos los descuentos propuestos
    descuentos = []
    # recorremos los periodos acreditados empezando por los mas antiguos
    for saldo in resumen.periodos_acreditados:
        if faltan <= 0:
            break
        if saldo.dias_disponibles <= 0:
            continue
        # min toma el menor valor entre los dias disponibles y los que faltan
        # asi no proponemos tomar mas de lo que tiene el saldo ni de lo que necesitamos
        dias = min(saldo.dias_disponibles, faltan)
        # añadimos a la lista el detalle de lo que se tomaria de este periodo
        descuentos.append(DescuentoPrevisto(
            id_saldo=saldo.id_saldo, periodo=saldo.periodo,
            dias_disponibles=saldo.dias_disponibles, dias_a_descontar=dias,
            # calculamos cuanto quedaria sin cambiar el saldo real de la base
            saldo_resultante=saldo.dias_disponibles - dias,
        ))
        # restamos de los dias pendientes la cantidad cubierta por este periodo
        faltan -= dias
        # resumen con los detalles dee la prevision
    return PrevisionRespuesta(
        id_empleado=id_empleado, fecha_consulta=resumen.fecha_consulta,
        dias_solicitados=calculo.dias_vacaciones,
        feriados_excluidos=calculo.feriados_excluidos,
        total_disponible=resumen.total_disponible,
        saldo_suficiente=faltan == 0, dias_sin_cobertura=faltan,
        descuentos=descuentos,
    )
