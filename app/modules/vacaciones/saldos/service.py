# usamos el día local del instituto, no la zona horaria del servidor
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
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
from app.modules.vacaciones.saldos.model import Saldo
from app.modules.vacaciones.saldos.repository import consultar_datos_empleado, insertar_periodos
from app.modules.vacaciones.saldos.schema import GeneracionPeriodosCrear, GeneracionPeriodosRespuesta
from app.modules.vacaciones.solicitudes.repository import bloquear_empleado
from app.modules.vacaciones.aprobaciones.repository import es_responsable_talento_humano

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


# calculamos cada aniversario desde la fecha original para conservar el 29 de febrero
# en años no bisiestos usamos el ultimo dia de febrero
def fecha_aniversario(fecha_ingreso: date, anios: int) -> date:
    from calendar import monthrange

    anio = fecha_ingreso.year + anios
    dia = min(fecha_ingreso.day, monthrange(anio, fecha_ingreso.month)[1])
    return date(anio, fecha_ingreso.month, dia)


# el numero indica los años completos que tendra al acreditar ese periodo
def dias_por_antiguedad(anios_completos: int) -> Decimal:
    if anios_completos < 1:
        raise ValueError("La asignación corresponde a un año de servicio completo.")
    return Decimal(min(30, 15 + max(0, anios_completos - 5))).quantize(Decimal("0.00"))


# crea los periodos faltantes hasta el periodo en curso, sin reescribir saldos anteriores
async def generar_periodos(
    sesion: AsyncSession, id_empleado: int, datos: GeneracionPeriodosCrear,
) -> GeneracionPeriodosRespuesta:
    hoy = fecha_actual()
    try:
        async with sesion.begin():
            if not await es_responsable_talento_humano(sesion, datos.id_responsable):
                raise HTTPException(status_code=403, detail="Responsable no habilitado en Talento Humano.")
            # compartimos el bloqueo de solicitudes y aprobaciones para no competir por el saldo
            await bloquear_empleado(sesion, id_empleado)
            empleado = await consultar_datos_empleado(sesion, id_empleado)
            ingreso = empleado["fecha_ingreso"]
            if empleado["estado"] is not True:
                raise HTTPException(status_code=409, detail="El empleado debe estar activo para generar períodos.")
            if ingreso is None or ingreso > hoy:
                raise HTTPException(status_code=409, detail="Revisa la fecha de ingreso del empleado en Core.")

            # esta consulta tambien valida cantidades, fechas, cruces y reservas existentes
            await obtener_resumen_saldo(sesion, id_empleado)
            existentes = await consultar_saldos_por_empleado(sesion, id_empleado)
            for saldo in existentes:
                anios = saldo.fecha_inicio_periodo.year - ingreso.year
                if (anios < 0 or saldo.fecha_inicio_periodo != fecha_aniversario(ingreso, anios)
                        or saldo.fecha_inicio_periodo.year >= 9999
                        or saldo.fecha_acreditacion != fecha_aniversario(ingreso, anios + 1)
                        or saldo.fecha_fin_periodo != saldo.fecha_acreditacion - timedelta(days=1)):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Revisa las fechas del saldo {saldo.id_saldo}: no coinciden con los aniversarios de ingreso. No se modificó ningún período.",
                    )

            anios_actuales = hoy.year - ingreso.year
            if fecha_aniversario(ingreso, anios_actuales) > hoy:
                anios_actuales -= 1
            inicio_actual = fecha_aniversario(ingreso, anios_actuales)
            # sin fecha explicita continuamos desde el ultimo periodo iniciado que ya conocemos
            # si no hay saldos, solo abrimos el actual; no suponemos vacaciones historicas sin usar
            inicios = [s.fecha_inicio_periodo for s in existentes if s.fecha_inicio_periodo <= hoy]
            desde = datos.fecha_desde or (max(inicios) if inicios else inicio_actual)
            anios_desde = desde.year - ingreso.year
            if (desde < ingreso or desde > hoy
                    or desde != fecha_aniversario(ingreso, anios_desde)):
                raise HTTPException(status_code=422, detail="fecha_desde debe ser el ingreso o un aniversario ya alcanzado del empleado.")
            if hoy.year >= 9999:
                raise HTTPException(status_code=422, detail="No se puede representar el siguiente aniversario.")

            por_inicio = {s.fecha_inicio_periodo: s for s in existentes}
            nuevos = []
            for anios in range(anios_desde, anios_actuales + 1):
                inicio = fecha_aniversario(ingreso, anios)
                if inicio in por_inicio:
                    # nunca reiniciamos utilizados, anticipos o reservas al repetir la operacion
                    continue
                acreditacion = fecha_aniversario(ingreso, anios + 1)
                asignados = dias_por_antiguedad(anios + 1)
                nuevos.append(Saldo(
                    id_empleado=id_empleado, periodo=f"{inicio.year}-{acreditacion.year}",
                    fecha_inicio_periodo=inicio,
                    fecha_fin_periodo=acreditacion - timedelta(days=1),
                    fecha_acreditacion=acreditacion,
                    dias_asignados=asignados, dias_utilizados=Decimal("0.00"),
                    dias_disponibles=asignados,
                ))
            await insertar_periodos(sesion, nuevos)
            respuesta = GeneracionPeriodosRespuesta(
                id_empleado=id_empleado, fecha_ingreso=ingreso, fecha_generacion=hoy,
                fecha_desde=desde, periodos_creados=[s.id_saldo for s in nuevos],
                periodos_conservados=[s.id_saldo for s in existentes],
                resumen=await obtener_resumen_saldo(sesion, id_empleado),
            )
    except IntegrityError:
        # un conflicto de integridad revierte tambien los periodos insertados previamente
        raise HTTPException(status_code=409, detail="No se pudieron generar los períodos. Revisa duplicados y restricciones de la base.") from None
    return respuesta
