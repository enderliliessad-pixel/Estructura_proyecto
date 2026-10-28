from sqlalchemy import select, text, table, column, BigInteger
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.solicitudes.model import Solicitud

# funcion para consultar solicitudes y trae una lista
async def consultar_solicitudes_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[Solicitud]:
    # consulta con la base
    consulta = (
        # seleccionar de la tabla solicitud
        # donde el id empleado sea igual a id empleado
        # ordenado por la fecha en forma descendente, los nulos al final
        # si existen 2 solicitudes al mismo tiempo, se va a ordenar por su id de forma descendente
        select(Solicitud)
        .where(Solicitud.id_empleado == id_empleado)
        .order_by(Solicitud.fecha_solicitud.desc().nulls_last(), Solicitud.id_solicitud.desc())
    )
    # se guarda en resultado la consulta y se devulve una lista
    resultado = await sesion.scalars(consulta)
    return list(resultado.all())

# funcion para consultar si un empleado existe a traves de una consulta de true o fals
async def existe_empleado(sesion: AsyncSession, id_empleado: int) -> bool:
    # la consulta esta en texto para indicar que solo traiga una existensi
    consulta = text(
            "SELECT EXISTS (SELECT 1 FROM core.empleados WHERE id_empleado = :id_empleado)"
        )
    # devolvera un booleano del texto con la solicitud.
    return bool(await sesion.scalar(consulta, {"id_empleado": id_empleado}))

# funcion para insertar una guardar una solicitud
async def insertar_solicitud(sesion: AsyncSession, solicitud: Solicitud) -> Solicitud:
    # se registra la solicitud
    sesion.add(solicitud)
    # uso de flush para generar el ID en la base de datos inmediatamente 
    # para poder utilizar ese ID en otro momentor
    await sesion.flush()
    # consulta para actualizar los datos
    await sesion.refresh(solicitud)
    # devolvemos el objeto completo y actualizado
    return solicitud

# funcion para actualizar una solicitud
async def consultar_solicitud_para_actualizar(
    sesion: AsyncSession, id_solicitud: int
    # devuelve una solicitud o nada si no encotro
) -> Solicitud | None:
    consulta = (
        select(Solicitud)
        .where(Solicitud.id_solicitud == id_solicitud)
        # esta seccion es para bloquear la pantalla por si 2 o mas personas aprueban la solocitud al mismo tiempo
        .with_for_update()
        # actualiza al momento exacto del cambio
        .execution_options(populate_existing=True)
    )
    return await sesion.scalar(consulta)

# funcion para consultar una solicitud por un id
async def consultar_solicitud_por_id(
    sesion: AsyncSession, id_solicitud: int
    # devuelv una solicitud o nada
) -> Solicitud | None:
    # la consulta indicando que de la tabla solicitud donde el id de solicitud sea igual al del id solicitud
    consulta =(
        select(Solicitud)
        .where(Solicitud.id_solicitud == id_solicitud)
    )
    return await sesion.scalar(consulta)

# funcion para guardar cambios de una solicitud
async def guardar_cambios_solicitud(
    sesion: AsyncSession, solicitud: Solicitud
) -> Solicitud:
    # uso de flush para generar el ID en la base de datos inmediatamente 
    # para poder utilizar ese ID en otro momentor
    await sesion.flush()
    # actualizar los datos
    await sesion.refresh(solicitud)
    # devolvemos el objeto completo y actualizado
    return solicitud

# funcion para serializar las operaciones de un mismo empleado, incluso si no tiene saldos
async def bloquear_empleado(sesion: AsyncSession, id_empleado: int) -> None:
    # FOR NO KEY UPDATE serializa al empleado sin bloquear las FK que solo leen su ID
    empleados = table("empleados", column("id_empleado", BigInteger), schema="core")
    consulta = select(empleados.c.id_empleado).where(empleados.c.id_empleado == id_empleado).with_for_update(key_share=True)
    if await sesion.scalar(consulta) is None:
        raise HTTPException(status_code=404, detail="El empleado no existe.")

# funcion para mantener el orden empleado, solicitud y luego saldos en todas las escrituras
async def bloquear_solicitud_y_empleado(sesion: AsyncSession, id_solicitud: int) -> Solicitud | None:
    id_empleado = await sesion.scalar(select(Solicitud.id_empleado).where(Solicitud.id_solicitud == id_solicitud))
    if id_empleado is None:
        solicitud = await consultar_solicitud_por_id(sesion, id_solicitud)
        if solicitud is not None:
            raise HTTPException(status_code=409, detail="La solicitud no tiene empleado asignado.")
        return None
    await bloquear_empleado(sesion, id_empleado)
    return await consultar_solicitud_para_actualizar(sesion, id_solicitud)

# funcion para buscar otra solicitud que comparta al menos un dia de ausencia
async def consultar_cruce(sesion: AsyncSession, id_empleado: int, inicio, fin, excluir: int | None = None):
    consulta = select(Solicitud.id_solicitud).where(
        Solicitud.id_empleado == id_empleado, Solicitud.tipo == "VACACIONES",
        Solicitud.estado.in_(["PENDIENTE", "APROBADA"]),
        Solicitud.fecha_inicio <= fin, Solicitud.fecha_fin >= inicio,
    )
    if excluir is not None:
        consulta = consulta.where(Solicitud.id_solicitud != excluir)
    return await sesion.scalar(consulta.limit(1))

# funcion para detectar solicitudes antiguas que aun no tienen una reserva conciliada
async def consultar_pendiente_sin_reserva(sesion: AsyncSession, id_empleado: int, excluir: int | None = None):
    consulta = select(Solicitud.id_solicitud).where(
        Solicitud.id_empleado == id_empleado, Solicitud.tipo == "VACACIONES",
        Solicitud.estado == "PENDIENTE", Solicitud.reserva_gestionada.is_(False),
    )
    if excluir is not None:
        consulta = consulta.where(Solicitud.id_solicitud != excluir)
    return await sesion.scalar(consulta.limit(1))