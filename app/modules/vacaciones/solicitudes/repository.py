from sqlalchemy import select, text
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
