from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.modules.vacaciones.calculos.router import router as calculo_router

from app.core.config import Configuracion, obtener_configuracion
from app.core.database import crear_sesiones, crear_conexion

from app.modules.vacaciones.aprobaciones.router import (router as aprobacion_router,)
from app.modules.vacaciones.feriados.router import (router as feriado_router,)
from app.modules.vacaciones.permisos.router import (router as permiso_router,)
from app.modules.vacaciones.saldos.router import (router as saldo_router,)
from app.modules.vacaciones.solicitudes.router import (router as solicitud_router,)

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
    aplicacion.include_router(calculo_router, prefix=prefijo)
    aplicacion.include_router(saldo_router, prefix=prefijo)
    aplicacion.include_router(solicitud_router, prefix=prefijo)
    aplicacion.include_router(aprobacion_router, prefix=prefijo)
    aplicacion.include_router(feriado_router, prefix=prefijo)
    aplicacion.include_router(permiso_router, prefix=prefijo)

    return aplicacion


app = crear_app()