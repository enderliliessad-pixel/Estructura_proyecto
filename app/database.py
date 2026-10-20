# manejo de flujo async
from collections.abc import AsyncIterator
# Las peticiones http que se hagan
from fastapi import Request
# herramientas de sqlalchemy para poder crear y asegurar sesiones
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import Configuracion

# creamos una clase principal llamada base
# utilizamos DeclarativeBase para decir que la clase se use como plantilla para decir cual es una tabla
# de sql y cual no
class Base(DeclarativeBase):
    # pass para indicar que esta clase no hace nada mas que ser una plantilla
    pass


def crear_conexion(configuracion: Configuracion):
    return create_async_engine(
        configuracion.url_base_datos(),
        # indicamos si la conexion existe antes de mandar consultas u otras acciones
        pool_pre_ping=True,
        # se mantiene limpia la consla de consultas innecesarias
        echo=False,
        # parametros no van a salir en los registros
        hide_parameters=True,
        # si la base no responde en 5 segundos se corta de forma automatica
        connect_args={"timeout": 5, "command_timeout": 5},
    )

# funcion para leer datos cuando se guardan en la base
def crear_sesiones(conexion):
    # configuracion de las sesion con la base de datos
    # uso de async_sessionmaker para realizar sesiones a la base 
    fabrica_sesiones = async_sessionmaker(
        # uso de bind para indicar que se va a utilizar una base en especifico
        bind=conexion,
        # uso de expire para poder ver datos aunquee se hayan guardado
        expire_on_commit=False,
    )
    
    return fabrica_sesiones

# funcion async para que pueda tomar mas de una peticion
# el request se usa para traer la peticion del usuario
# Async se usa para indicar que se va a entregar un flujo asincrono de tipo AsyncSession
async def obtener_sesion(request: Request) -> AsyncIterator[AsyncSession]:
    # peticion asincrona que abre una sesion temporal que se cierra automaticamente al terminar la peticion
    async with request.app.state.sesiones() as sesion:
        yield sesion
# usamos yield para indicar que la sesion obtenida no se cierre automaticamente sino que se realize el proceso
# y una vez teerminado vuelva para cerrarse
