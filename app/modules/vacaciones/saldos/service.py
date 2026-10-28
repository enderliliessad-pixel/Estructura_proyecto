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
from app.modules.vacaciones.reservas.repository import consultar_reservas_activas

# funcion async para obtener los saldos y devuelve una lista
async def obtener_saldos_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[SaldoRespuesta]:
    # la consulta se guarda en saldo
    saldos = await consultar_saldos_por_empleado(sesion, id_empleado)
    # el return transforma los modelos de base la base de datos en esquemas Json que la web sabe leer
    reservas = await consultar_reservas_activas(sesion, id_empleado)
    respuestas = []
    for saldo in saldos:
        respuesta = SaldoRespuesta.model_validate(saldo)
        respuesta.dias_reservados = sum((r.dias_reservados for r in reservas if r.id_saldo == saldo.id_saldo), Decimal("0.00"))
        respuesta.dias_libres = max(Decimal("0.00"), (saldo.dias_disponibles or Decimal("0.00")) - respuesta.dias_reservados)
        respuestas.append(respuesta)
    return respuestas

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
            raise HTTPException(status_code=409, detail=f"El saldo {saldo.id_saldo} contiene cantidades incompletas, negativas o inválidas.")
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
    # las reservas se consultan juntas para evitar una consulta adicional por periodo
    reservas = await consultar_reservas_activas(sesion, id_empleado)
    respuestas = {}
    for saldo in saldos:
        respuesta = SaldoRespuesta.model_validate(saldo)
        respuesta.dias_reservados = sum((r.dias_reservados for r in reservas if r.id_saldo == saldo.id_saldo), Decimal("0.00"))
        if respuesta.dias_reservados > saldo.dias_disponibles:
            raise HTTPException(status_code=409, detail=f"Las reservas del saldo {saldo.id_saldo} superan su disponibilidad.")
        respuesta.dias_libres = saldo.dias_disponibles - respuesta.dias_reservados
        respuestas[saldo.id_saldo] = respuesta
    # solo se anticipa el periodo que se esta trabajando; no se encadenan años futuros
    for saldo in futuros:
        if saldo.fecha_inicio_periodo <= hoy <= saldo.fecha_fin_periodo:
            respuesta = respuestas[saldo.id_saldo]
            if saldo.dias_utilizados + respuesta.dias_reservados > Decimal("15.00"):
                raise HTTPException(status_code=409, detail=f"El saldo {saldo.id_saldo} supera los 15 días anticipados del período.")
            respuesta.dias_anticipables = max(Decimal("0.00"), min(
                respuesta.dias_libres, Decimal("15.00") - saldo.dias_utilizados - respuesta.dias_reservados,
            ))
    return ResumenSaldoRespuesta(
        id_empleado=id_empleado, fecha_consulta=hoy,
        total_disponible=sum((respuestas[s.id_saldo].dias_libres for s in acreditados), Decimal("0.00")),
        total_reservado=sum((r.dias_reservados for r in reservas), Decimal("0.00")),
        total_anticipable=sum((respuestas[s.id_saldo].dias_anticipables for s in futuros), Decimal("0.00")),
        periodos_acreditados=[respuestas[s.id_saldo] for s in acreditados],
        periodos_no_acreditados=[respuestas[s.id_saldo] for s in futuros],
    )

# funcion para repartir primero los dias antiguos y despues el anticipo del periodo en curso
def distribuir_dias(resumen: ResumenSaldoRespuesta, dias: Decimal):
    faltan = dias
    descuentos = []
    for saldo in resumen.periodos_acreditados + resumen.periodos_no_acreditados:
        anticipo = saldo.fecha_acreditacion > resumen.fecha_consulta
        disponibles = saldo.dias_anticipables if anticipo else saldo.dias_libres
        if faltan <= 0:
            break
        if disponibles <= 0:
            continue
        tomar = min(disponibles, faltan)
        descuentos.append(DescuentoPrevisto(
            id_saldo=saldo.id_saldo, periodo=saldo.periodo,
            dias_disponibles=disponibles, dias_a_descontar=tomar,
            saldo_resultante=saldo.dias_libres - tomar, es_anticipo=anticipo,
        ))
        faltan -= tomar
    return descuentos, faltan

# funcion para prever de que periodos se tomarian los dias solicitados
# solo calcula y consulta, no guarda descuentos ni modifica los saldos
async def prever_descuentos(
    sesion: AsyncSession, id_empleado: int, fecha_inicio: date, fecha_fin: date
) -> PrevisionRespuesta:
    calculo = await calcular_dias_vacaciones(sesion, fecha_inicio, fecha_fin)
    resumen = await obtener_resumen_saldo(sesion, id_empleado)
    descuentos, faltan = distribuir_dias(resumen, calculo.dias_vacaciones)
    return PrevisionRespuesta(
        id_empleado=id_empleado, fecha_consulta=resumen.fecha_consulta,
        dias_solicitados=calculo.dias_vacaciones,
        feriados_excluidos=calculo.feriados_excluidos,
        total_disponible=resumen.total_disponible,
        total_anticipable=resumen.total_anticipable,
        saldo_suficiente=faltan == 0, dias_sin_cobertura=faltan,
        descuentos=descuentos,
    )
