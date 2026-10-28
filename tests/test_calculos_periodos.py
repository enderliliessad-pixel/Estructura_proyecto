import asyncio
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import obtener_sesion
from app.modules.vacaciones.calculos.router import router as calculos
from app.modules.vacaciones.saldos.router import router as saldos
from app.modules.vacaciones.solicitudes.router import router as solicitudes
from app.modules.vacaciones.saldos import service as saldos_service


@pytest.fixture
def db(monkeypatch):
    # SQLite verifica cálculos y transacciones; no sustituye las pruebas de PostgreSQL.
    engine = create_async_engine('sqlite+aiosqlite://', poolclass=StaticPool)
    @event.listens_for(engine.sync_engine, 'connect')
    def conectar(conn, record):
        conn.execute("ATTACH DATABASE ':memory:' AS vacaciones")
        conn.execute("ATTACH DATABASE ':memory:' AS core")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async def setup():
        async with engine.begin() as c:
            for sql in [
                'CREATE TABLE core.empleados (id_empleado INTEGER PRIMARY KEY)',
                'INSERT INTO core.empleados VALUES (1),(2)',
                'CREATE TABLE vacaciones.feriados (id_feriado INTEGER PRIMARY KEY, fecha DATE, descripcion TEXT, tipo TEXT, estado BOOLEAN)',
                '''CREATE TABLE vacaciones.saldos (id_saldo INTEGER PRIMARY KEY, id_empleado BIGINT, periodo TEXT, dias_asignados NUMERIC, dias_utilizados NUMERIC, dias_disponibles NUMERIC, fecha_inicio_periodo DATE, fecha_fin_periodo DATE, fecha_acreditacion DATE)''',
                '''INSERT INTO vacaciones.saldos VALUES
                (20,1,'Anterior',15,12,3,'2023-11-15','2024-11-14','2024-11-15'),
                (10,1,'Actual',15,0,15,'2024-11-15','2025-11-14','2025-11-15'),
                (30,1,'Futuro',15,0,15,'2025-11-15','2026-11-14','2026-11-15')''',
                '''CREATE TABLE vacaciones.solicitudes (id_solicitud INTEGER PRIMARY KEY AUTOINCREMENT, id_empleado BIGINT, tipo TEXT, fecha_inicio DATE, fecha_fin DATE, dias_solicitados NUMERIC, horas_solicitadas NUMERIC, motivo TEXT, estado TEXT, fecha_solicitud TIMESTAMP)''',
                '''CREATE TABLE vacaciones.aprobaciones (id_aprobacion INTEGER PRIMARY KEY, id_solicitud BIGINT, id_aprobador BIGINT, fecha TIMESTAMP, decision TEXT, observacion TEXT)''',
                'CREATE TABLE vacaciones.descuentos_por_periodo (id_descuento INTEGER PRIMARY KEY, id_solicitud BIGINT, id_saldo BIGINT, dias_descontados NUMERIC)',
            ]:
                await c.execute(text(sql))
    asyncio.run(setup())
    monkeypatch.setattr(saldos_service, 'fecha_actual', lambda: date(2026,10,27))
    app = FastAPI()
    for r in (calculos,saldos,solicitudes): app.include_router(r)
    async def sesion():
        async with factory() as s: yield s
    app.dependency_overrides[obtener_sesion] = sesion
    async def leer(sql):
        async with factory() as s: return (await s.execute(text(sql))).all()
    async def escribir(sql):
        async with factory.begin() as s: await s.execute(text(sql))
    with TestClient(app) as c:
        yield c,lambda sql: asyncio.run(leer(sql)),lambda sql: asyncio.run(escribir(sql))
    asyncio.run(engine.dispose())


def consulta(c, inicio, fin, ruta='/calculos/dias'):
    return c.get(ruta, params={'fecha_inicio':inicio,'fecha_fin':fin})


@pytest.mark.parametrize('inicio,fin,dias',[
    ('2026-11-06','2026-11-08',3), # viernes, sábado y domingo
    ('2026-11-06','2026-11-09',4), # lunes incluido como ausencia
    ('2026-11-09','2026-11-09',1),
    ('2028-02-28','2028-03-01',3),
    ('2026-12-31','2027-01-01',2),
])
def test_calendario(db,inicio,fin,dias):
    c,_,_=db;r=consulta(c,inicio,fin)
    assert r.status_code==200
    assert Decimal(r.json()['dias_vacaciones'])==dias


def test_feriados_unicos_activos(db):
    c,_,e=db
    e("INSERT INTO vacaciones.feriados VALUES (1,'2026-11-10','A','PRUEBA',1),(2,'2026-11-10','B','PRUEBA',1),(3,'2026-11-09','C','PRUEBA',0),(4,'2026-11-11','D','PRUEBA',NULL)")
    r=consulta(c,'2026-11-09','2026-11-10').json()
    assert r['feriados_excluidos']==['2026-11-10']
    assert Decimal(r['dias_vacaciones'])==1
    assert Decimal(consulta(c,'2026-11-10','2026-11-10').json()['dias_vacaciones'])==0


@pytest.mark.parametrize('inicio,fin',[
    ('2026-11-10','2026-11-09'),('2026-02-30','2026-03-01'),('2000-01-01','2100-01-01'),
])
def test_fechas_invalidas(db,inicio,fin):
    assert consulta(db[0],inicio,fin).status_code==422


def test_resumen_y_prevision_fifo_sin_escrituras(db):
    c,q,_=db;antes=q('SELECT * FROM vacaciones.saldos')
    r=c.get('/saldos/1/resumen').json()
    assert Decimal(r['total_disponible'])==18
    assert [s['id_saldo'] for s in r['periodos_acreditados']]==[20,10]
    assert [s['id_saldo'] for s in r['periodos_no_acreditados']]==[30]
    r=consulta(c,'2026-11-09','2026-11-13','/saldos/1/prevision').json()
    assert r['saldo_suficiente'] is True
    assert [(d['id_saldo'],Decimal(d['dias_a_descontar'])) for d in r['descuentos']]==[(20,3),(10,2)]
    assert Decimal(r['descuentos'][1]['saldo_resultante'])==13
    assert q('SELECT * FROM vacaciones.saldos')==antes
    assert q('SELECT count(*) FROM vacaciones.descuentos_por_periodo')==[(0,)]


def test_insuficiente_no_usa_futuro(db):
    c,_,_=db
    r=consulta(c,'2027-01-01','2027-01-20','/saldos/1/prevision').json()
    assert r['saldo_suficiente'] is False
    assert Decimal(r['dias_sin_cobertura'])==2
    assert all(d['id_saldo']!=30 for d in r['descuentos'])


def test_aniversario_incluye_saldo_ya_registrado(db,monkeypatch):
    c,_,_=db;monkeypatch.setattr(saldos_service,'fecha_actual',lambda:date(2026,11,15))
    r=c.get('/saldos/1/resumen').json()
    assert Decimal(r['total_disponible'])==33
    assert r['periodos_no_acreditados']==[]


def test_empleado_sin_saldos_e_inexistente(db):
    c,_,_=db
    assert Decimal(c.get('/saldos/2/resumen').json()['total_disponible'])==0
    r=consulta(c,'2026-11-09','2026-11-13','/saldos/2/prevision').json()
    assert Decimal(r['dias_sin_cobertura'])==5 and r['descuentos']==[]
    assert c.get('/saldos/999/resumen').status_code==404


@pytest.mark.parametrize('cambio',[
    'fecha_inicio_periodo=NULL',
    "fecha_fin_periodo='2020-01-01'",
    'dias_disponibles=NULL',
    'dias_disponibles=-1',
    'dias_disponibles=9',
    "fecha_inicio_periodo='2024-01-01'", # se superpone con el anterior
])
def test_saldos_incompletos_o_inconsistentes(db,cambio):
    c,_,e=db;e('UPDATE vacaciones.saldos SET '+cambio+' WHERE id_saldo=10')
    assert c.get('/saldos/1/resumen').status_code==409
    assert consulta(c,'2026-11-09','2026-11-13','/saldos/1/prevision').status_code==409


def test_fracciones_ya_existentes(db):
    c,_,e=db;e('UPDATE vacaciones.saldos SET dias_utilizados=14.5,dias_disponibles=0.5 WHERE id_saldo=20')
    r=consulta(c,'2026-11-09','2026-11-09','/saldos/1/prevision').json()
    assert [Decimal(d['dias_a_descontar']) for d in r['descuentos']]==[Decimal('0.5'),Decimal('0.5')]


def test_crear_editar_dias_calculados(db):
    c,q,e=db
    e("INSERT INTO vacaciones.feriados VALUES (1,'2026-11-10','A','PRUEBA',1)")
    datos={'id_empleado':1,'fecha_inicio':'2026-11-09','fecha_fin':'2026-11-10','motivo':'Prueba'}
    r=c.post('/solicitudes',json=datos)
    assert r.status_code==201,r.text
    assert Decimal(r.json()['dias_solicitados'])==1
    assert r.json()['estado']=='PENDIENTE'
    assert c.post('/solicitudes',json={**datos,'dias_solicitados':2}).status_code==422
    editar={'fecha_inicio':'2026-11-06','fecha_fin':'2026-11-08','motivo':'Cambio'}
    r=c.put('/solicitudes/detalle/1',json=editar)
    assert r.status_code==200 and Decimal(r.json()['dias_solicitados'])==3
    assert c.put('/solicitudes/detalle/1',json={**editar,'dias_solicitados':1}).status_code==422
    assert q('SELECT dias_solicitados FROM vacaciones.solicitudes WHERE id_solicitud=1')==[(3,)]
    assert q('SELECT dias_disponibles FROM vacaciones.saldos WHERE id_saldo=20')==[(3,)]


def test_no_crea_solicitud_solo_feriados(db):
    c,q,e=db;e("INSERT INTO vacaciones.feriados VALUES (1,'2026-11-10','A','PRUEBA',1)")
    r=c.post('/solicitudes',json={'id_empleado':1,'fecha_inicio':'2026-11-10','fecha_fin':'2026-11-10','motivo':'Prueba'})
    assert r.status_code==422
    assert q('SELECT count(*) FROM vacaciones.solicitudes')==[(0,)]
