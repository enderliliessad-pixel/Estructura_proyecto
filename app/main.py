from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Configuracion, obtener_configuracion
from app.database import crear_sesiones, crear_conexion

from app.modules.vacaciones.controllers.aprobacion_controller import (router as aprobacion_router,)
from app.modules.vacaciones.controllers.feriado_controller import (router as feriado_router,)
from app.modules.vacaciones.controllers.permiso_controller import (router as permiso_router,)
from app.modules.vacaciones.controllers.saldo_controller import (router as saldo_router,)
from app.modules.vacaciones.controllers.solicitud_controller import (router as solicitud_router,)

# crearmos una funcion que traiga la configuracion o nada si no resive datos.
def crear_app(configuracion: Configuracion | None = None) -> FastAPI:
    # usamos el asynccontextmanager para definir el momento de aranque y cierre del servidor
    @asynccontextmanager
    async def produccion_app(app: FastAPI):
        # indicamos que no resive una configuracion traela directamente de app.config

        if configuracion is None:
            ajustes = obtener_configuracion()
        else:
            # caso contrario trae la configuracion
            ajustes = configuracion
        # iniciamos la conexion con la base y la guardamos en conexion
        conexion = crear_conexion(ajustes)

        try:
            # uso de try para indicar que se guarde la conexion
            app.state.sesiones = crear_sesiones(conexion)

            yield
        # uso de await para cerrar cualquier operacion una vez se apague el servidor
        finally:

            await conexion.dispose()
    # interfaz visual del fastAPI
    aplicacion = FastAPI(
        title="API de Vacaciones",
        version="0.1.0",
        description=(
            "Consultas de vacaciones. "
            "Registro, aprobación y cálculos pendientes."
        ),
        lifespan=produccion_app,
    )

    # Dirección común para las rutas del módulo.
    prefijo = "/api/v1/vacaciones"
    # las rutas con el prefijo
    aplicacion.include_router(saldo_router, prefix=prefijo)
    aplicacion.include_router(solicitud_router, prefix=prefijo)
    aplicacion.include_router(aprobacion_router, prefix=prefijo)
    aplicacion.include_router(feriado_router, prefix=prefijo)
    aplicacion.include_router(permiso_router, prefix=prefijo)

    return aplicacion


app = crear_app()