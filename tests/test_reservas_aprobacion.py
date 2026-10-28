from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError
from test_calculos_periodos import db

# estas pruebas recorren la API con base temporal, sin leer el .env del usuario

def crear(c, inicio='2026-11-01', fin='2026-11-05', empleado=1):
    return c.post('/solicitudes', json={'id_empleado':empleado,'fecha_inicio':inicio,
                                      'fecha_fin':fin,'motivo':'Vacaciones de prueba'})

def aprobar(c, solicitud=1, aprobador=2):
    return c.post(f'/solicitudes/{solicitud}/aprobacion',json={'id_aprobador':aprobador,'observacion':'Documento revisado por TH'})

def test_reserva_fifo_y_aprobacion_sin_doble_descuento(db):
    c,q,_=db
    assert crear(c).status_code==201
    assert q('SELECT dias_disponibles FROM vacaciones.saldos ORDER BY id_saldo')==[(15,),(3,),(15,)]
    r=c.get('/saldos/1/resumen').json()
    assert Decimal(r['total_disponible'])==13 and Decimal(r['total_reservado'])==5
    reservas=c.get('/solicitudes/detalle/1/reservas').json()
    assert [(r['id_saldo'],Decimal(r['dias_reservados'])) for r in reservas]==[(20,3),(10,2)]
    assert aprobar(c).status_code==201
    assert q('SELECT dias_disponibles FROM vacaciones.saldos ORDER BY id_saldo')==[(13,),(0,),(15,)]
    assert q('SELECT count(*) FROM vacaciones.descuentos_por_periodo')==[(2,)]
    assert aprobar(c).status_code==409
    assert q('SELECT count(*) FROM vacaciones.descuentos_por_periodo')==[(2,)]
    assert q("SELECT count(*) FROM vacaciones.reservas_por_periodo WHERE estado='CONSUMIDA'")==[(2,)]
    assert Decimal(c.get('/saldos/1/resumen').json()['total_disponible'])==13

@pytest.mark.parametrize('ruta', ['cancelar','rechazo'])
def test_liberar_reserva(db,ruta):
    c,q,_=db;assert crear(c).status_code==201
    if ruta=='cancelar':
        r=c.patch('/solicitudes/detalle/1/cancelar')
    else:
        r=c.post('/solicitudes/1/rechazo',json={'id_aprobador':2,'observacion':'No procede'})
    assert r.status_code in (200,201)
    assert Decimal(c.get('/saldos/1/resumen').json()['total_disponible'])==18
    assert q("SELECT count(*) FROM vacaciones.reservas_por_periodo WHERE estado='ACTIVA'")==[(0,)]
    assert q('SELECT count(*) FROM vacaciones.descuentos_por_periodo')==[(0,)]
    assert aprobar(c).status_code==409
    # un documento rechazado o cancelado no bloquea una nueva solicitud en las mismas fechas
    assert crear(c).status_code==201

@pytest.mark.parametrize('inicio,fin', [('2026-11-05','2026-11-08'),('2026-11-02','2026-11-03'),('2026-10-31','2026-11-06')])
def test_cruce_pendiente_y_aprobada(db,inicio,fin):
    c,q,_=db;assert crear(c).status_code==201
    assert crear(c,inicio,fin).status_code==409
    assert aprobar(c).status_code==201
    assert crear(c,inicio,fin).status_code==409
    assert q('SELECT count(*) FROM vacaciones.solicitudes')==[(1,)]


def test_no_cruza_otro_empleado_y_fechas_adyacentes(db):
    c,_,e=db;assert crear(c).status_code==201
    e("INSERT INTO vacaciones.saldos VALUES (40,2,'Actual',15,0,15,'2024-11-15','2025-11-14','2025-11-15')")
    assert crear(c,empleado=2).status_code==201
    assert crear(c,'2026-11-06','2026-11-06').status_code==201


def test_editar_recalcula_reserva_y_fallo_restaura_original(db):
    c,q,_=db;assert crear(c).status_code==201
    datos={'fecha_inicio':'2026-11-01','fecha_fin':'2026-11-02','motivo':'Acortar'}
    assert c.put('/solicitudes/detalle/1',json=datos).status_code==200
    assert Decimal(c.get('/saldos/1/resumen').json()['total_disponible'])==16
    antes=q('SELECT * FROM vacaciones.reservas_por_periodo')
    r=c.put('/solicitudes/detalle/1',json={**datos,'fecha_fin':'2026-12-31'})
    assert r.status_code==409
    assert q('SELECT * FROM vacaciones.reservas_por_periodo')==antes
    assert q('SELECT dias_solicitados FROM vacaciones.solicitudes')==[(2,)]


def test_editar_no_permite_cruce_ni_cambiar_aprobada(db):
    c,_,_=db;assert crear(c).status_code==201
    assert crear(c,'2026-11-10','2026-11-11').status_code==201
    datos={'fecha_inicio':'2026-11-05','fecha_fin':'2026-11-10','motivo':'Cruce'}
    assert c.put('/solicitudes/detalle/2',json=datos).status_code==409
    assert aprobar(c).status_code==201
    assert c.put('/solicitudes/detalle/1',json=datos).status_code==409
    assert c.patch('/solicitudes/detalle/1/cancelar').status_code==409


def test_anticipo_limite_acumulado_por_periodo(db):
    c,q,e=db
    e('UPDATE vacaciones.saldos SET dias_utilizados=15,dias_disponibles=0 WHERE id_saldo IN (10,20)')
    assert crear(c,'2026-11-01','2026-11-10').status_code==201
    assert crear(c,'2026-12-01','2026-12-06').status_code==409
    assert crear(c,'2026-12-01','2026-12-05').status_code==201
    r=c.get('/saldos/1/resumen').json()
    assert Decimal(r['total_anticipable'])==0
    assert aprobar(c).status_code==201
    assert crear(c,'2027-01-01','2027-01-01').status_code==409
    assert q('SELECT dias_utilizados,dias_disponibles FROM vacaciones.saldos WHERE id_saldo=30')==[(10,5)]
    assert aprobar(c,solicitud=2).status_code==201
    assert q('SELECT dias_utilizados,dias_disponibles FROM vacaciones.saldos WHERE id_saldo=30')==[(15,0)]


def test_no_anticipa_periodos_que_no_han_empezado(db):
    c,_,e=db
    e('UPDATE vacaciones.saldos SET dias_utilizados=15,dias_disponibles=0')
    e("INSERT INTO vacaciones.saldos VALUES (40,1,'Remoto',15,0,15,'2026-11-15','2027-11-14','2027-11-15')")
    assert crear(c).status_code==409


def test_anticipo_para_empleado_sin_primer_aniversario(db):
    c,_,e=db
    e("INSERT INTO vacaciones.saldos VALUES (40,2,'Primer año',15,0,15,'2026-02-01','2027-01-31','2027-02-01')")
    assert crear(c,empleado=2).status_code==201
    assert c.get('/solicitudes/detalle/1/reservas').json()[0]['es_anticipo'] is True


def test_limite_20_con_acumulados(db):
    c,q,e=db
    e('UPDATE vacaciones.saldos SET dias_asignados=30,dias_utilizados=0,dias_disponibles=30 WHERE id_saldo=20')
    assert crear(c,'2026-11-01','2026-11-21').status_code==422
    assert q('SELECT count(*) FROM vacaciones.solicitudes')==[(0,)]
    assert crear(c,'2026-11-01','2026-11-20').status_code==201


def test_no_habilitado_no_puede_aprobar_ni_rechazar(db):
    c,q,_=db;assert crear(c).status_code==201
    assert aprobar(c,aprobador=1).status_code==403
    assert aprobar(c,aprobador=999).status_code==404
    assert c.post('/solicitudes/1/rechazo',json={'id_aprobador':1,'observacion':'No'}).status_code==403
    assert q("SELECT estado FROM vacaciones.solicitudes")==[('PENDIENTE',)]
    assert q('SELECT count(*) FROM vacaciones.descuentos_por_periodo')==[(0,)]


def test_fallo_durante_aprobacion_revierte_saldo_reservas_y_decision(db,monkeypatch):
    from app.modules.vacaciones.aprobaciones import service
    c,q,_=db;assert crear(c).status_code==201
    antes=q('SELECT * FROM vacaciones.saldos')
    async def fallar(*args):
        raise RuntimeError('Fallo simulado al insertar la decisión')
    monkeypatch.setattr(service,'insertar_aprobacion',fallar)
    with pytest.raises(RuntimeError): aprobar(c)
    assert q('SELECT * FROM vacaciones.saldos')==antes
    assert q("SELECT count(*) FROM vacaciones.reservas_por_periodo WHERE estado='ACTIVA'")==[(2,)]
    assert q('SELECT count(*) FROM vacaciones.descuentos_por_periodo')==[(0,)]
    assert q('SELECT estado FROM vacaciones.solicitudes')==[('PENDIENTE',)]


def test_saldo_modificado_manualmente_no_admite_descuento_inconsistente(db):
    c,q,e=db;assert crear(c).status_code==201
    e('UPDATE vacaciones.saldos SET dias_utilizados=15,dias_disponibles=0 WHERE id_saldo=20')
    assert aprobar(c).status_code==409
    assert q('SELECT count(*) FROM vacaciones.aprobaciones')==[(0,)]


def test_conciliacion_de_pendiente_antiguo(db):
    c,q,e=db
    e("INSERT INTO vacaciones.solicitudes VALUES (7,1,'VACACIONES','2026-11-01','2026-11-02',2,0,'Antigua','PENDIENTE','2026-10-20',FALSE)")
    assert aprobar(c,solicitud=7).status_code==409
    assert crear(c,'2026-12-01','2026-12-01').status_code==409
    assert c.post('/solicitudes/detalle/7/reserva').status_code==200
    assert c.post('/solicitudes/detalle/7/reserva').status_code==409
    assert aprobar(c,solicitud=7).status_code==201
    assert q('SELECT count(*) FROM vacaciones.descuentos_por_periodo')==[(1,)]


def test_aniversario_no_borra_anticipos_ni_reservas(db,monkeypatch):
    from datetime import date
    from app.modules.vacaciones.saldos import service
    c,q,e=db
    e('UPDATE vacaciones.saldos SET dias_utilizados=15,dias_disponibles=0 WHERE id_saldo IN (10,20)')
    assert crear(c).status_code==201
    monkeypatch.setattr(service,'fecha_actual',lambda:date(2026,11,15))
    resumen=c.get('/saldos/1/resumen').json()
    assert Decimal(resumen['total_disponible'])==10
    assert aprobar(c).status_code==201
    assert Decimal(c.get('/saldos/1/resumen').json()['total_disponible'])==10
    assert q('SELECT es_anticipo FROM vacaciones.descuentos_por_periodo')==[(1,)]
