"""Pruebas optativas en una base PostgreSQL VACIA dedicada, nunca desde .env.
VACACIONES_TEST_DATABASE_URL=postgresql+asyncpg://.../itq_pruebas_vacaciones
No usar con datos reales. El nombre debe terminar en _pruebas_vacaciones.
"""
import asyncio
import os
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.modules.vacaciones.solicitudes.service import crear_solicitud
from app.modules.vacaciones.solicitudes.schema import SolicitudCrear
from app.modules.vacaciones.aprobaciones.service import aprobar_solicitud
from app.modules.vacaciones.aprobaciones.schema import AprobacionCrear
from app.modules.vacaciones.saldos import service as saldos_service

URL = os.environ.get('VACACIONES_TEST_DATABASE_URL')
PGLITE = os.environ.get('VACACIONES_TEST_PGLITE') == '1'
pytestmark = pytest.mark.skipif(not URL, reason='Requiere base PostgreSQL de pruebas explícita; no usa .env')


def conexion():
    return create_async_engine(URL, pool_size=1 if PGLITE else 5, max_overflow=0, connect_args={"timeout":5,"command_timeout":10,"ssl":False})

@pytest.fixture(scope='module', autouse=True)
def preparar_postgresql():
    if not URL:
        yield
        return
    url=make_url(URL)
    if url.drivername != 'postgresql+asyncpg' or not (url.database or '').endswith('_pruebas_vacaciones'):
        pytest.fail('La URL debe usar asyncpg y una base terminada en _pruebas_vacaciones')
    async def preparar():
        engine=conexion()
        try:
            async with engine.connect() as c:
                existente=await c.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname IN ('core','vacaciones'))"))
                if existente:
                    pytest.fail('La base de pruebas ya contiene core/vacaciones; crea una base vacía nueva')
                raw=await c.get_raw_connection()
                for nombre in ['01_core_dependencias.sql','02_vacaciones.sql','03_periodos_y_descuentos.sql','04_reservas_y_aprobacion.sql','04_reservas_y_aprobacion.sql']:
                    sql=(Path(__file__).resolve().parents[1]/'sql'/nombre).read_text()
                    if PGLITE:
                        sql=sql.replace('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";','')
                    await raw.driver_connection.execute(sql)
        finally:
            await engine.dispose()
    asyncio.run(preparar())
    yield
    # La base queda disponible para inspeccion; no se elimina automaticamente.

@pytest.fixture
def escenario(monkeypatch):
    monkeypatch.setattr(saldos_service,'fecha_actual',lambda:date(2026,10,27))
    async def ejecutar(prueba):
        engine=conexion();factory=async_sessionmaker(engine,expire_on_commit=False)
        try:
            async with engine.begin() as c:
                # Solo en la base vacia dedicada que ha creado este modulo.
                await c.execute(text('TRUNCATE vacaciones.reservas_por_periodo, vacaciones.descuentos_por_periodo, vacaciones.aprobaciones, vacaciones.solicitudes, vacaciones.saldos, vacaciones.responsables_talento_humano, core.empleados RESTART IDENTITY CASCADE'))
                await c.execute(text('INSERT INTO core.empleados(id_empleado) VALUES (1),(2)'))
                await c.execute(text('INSERT INTO vacaciones.responsables_talento_humano VALUES (2,TRUE)'))
                await c.execute(text("INSERT INTO vacaciones.saldos(id_empleado,periodo,dias_asignados,dias_utilizados,dias_disponibles,fecha_inicio_periodo,fecha_fin_periodo,fecha_acreditacion) VALUES (1,'2026-2027',15,0,15,'2026-02-01','2027-01-31','2027-02-01')"))
            await prueba(factory)
        finally:
            await engine.dispose()
    return lambda prueba: asyncio.run(ejecutar(prueba))

async def alta(factory,inicio='2026-11-01',fin='2026-11-10'):
    async with factory() as sesion:
        try:
            r=await crear_solicitud(sesion,SolicitudCrear(id_empleado=1,fecha_inicio=inicio,fecha_fin=fin,motivo='Prueba PostgreSQL'))
            return r.id_solicitud
        except HTTPException as e:
            return e.status_code

async def aprobar(factory,solicitud):
    async with factory() as sesion:
        try:
            await aprobar_solicitud(sesion,solicitud,AprobacionCrear(id_aprobador=2,observacion='Prueba TH'))
            return 201
        except HTTPException as e:
            return e.status_code


def test_postgresql_reserva_descuento_y_repeticion(escenario):
    async def prueba(factory):
        solicitud=await alta(factory)
        assert solicitud==1
        assert await aprobar(factory,solicitud)==201
        assert await aprobar(factory,solicitud)==409
        async with factory() as s:
            assert await s.scalar(text('SELECT dias_disponibles FROM vacaciones.saldos'))==5
            assert await s.scalar(text('SELECT count(*) FROM vacaciones.descuentos_por_periodo'))==1
            assert await s.scalar(text("SELECT count(*) FROM vacaciones.reservas_por_periodo WHERE estado='CONSUMIDA'"))==1
    escenario(prueba)


def test_postgresql_restricciones_y_rollback(escenario):
    from sqlalchemy.exc import IntegrityError
    async def prueba(factory):
        await alta(factory)
        for sql in [
            "INSERT INTO vacaciones.reservas_por_periodo(id_empleado,id_solicitud,id_saldo,dias_reservados,es_anticipo,estado) VALUES (1,1,1,1,TRUE,'ACTIVA')",
            "INSERT INTO vacaciones.reservas_por_periodo(id_empleado,id_solicitud,id_saldo,dias_reservados,es_anticipo,estado) VALUES (2,1,1,1,TRUE,'ACTIVA')",
            "UPDATE vacaciones.saldos SET dias_disponibles=-1",
            "DELETE FROM vacaciones.solicitudes WHERE id_solicitud=1",
        ]:
            async with factory() as s:
                with pytest.raises(IntegrityError):
                    async with s.begin(): await s.execute(text(sql))
        async with factory() as s:
            assert await s.scalar(text('SELECT dias_disponibles FROM vacaciones.saldos'))==15
    escenario(prueba)


@pytest.mark.skipif(PGLITE,reason='PGlite no reproduce la concurrencia real de PostgreSQL')
@pytest.mark.parametrize('mismo_intervalo',[False,True])
def test_postgresql_dos_altas_simultaneas(escenario,mismo_intervalo):
    async def prueba(factory):
        segunda=('2026-11-01','2026-11-10') if mismo_intervalo else ('2026-12-01','2026-12-10')
        resultados=await asyncio.wait_for(asyncio.gather(alta(factory),alta(factory,*segunda)),timeout=15)
        assert sum(r==409 for r in resultados)==1
        async with factory() as s:
            assert await s.scalar(text('SELECT count(*) FROM vacaciones.solicitudes'))==1
            assert await s.scalar(text("SELECT sum(dias_reservados) FROM vacaciones.reservas_por_periodo WHERE estado='ACTIVA'"))==10
    escenario(prueba)


@pytest.mark.skipif(PGLITE,reason='PGlite no reproduce la concurrencia real de PostgreSQL')
def test_postgresql_dos_aprobaciones_simultaneas(escenario):
    async def prueba(factory):
        solicitud=await alta(factory)
        resultados=await asyncio.wait_for(asyncio.gather(aprobar(factory,solicitud),aprobar(factory,solicitud)),timeout=15)
        assert sorted(resultados)==[201,409]
        async with factory() as s:
            assert await s.scalar(text('SELECT dias_disponibles FROM vacaciones.saldos'))==5
            assert await s.scalar(text('SELECT count(*) FROM vacaciones.descuentos_por_periodo'))==1
    escenario(prueba)
