from datetime import date
from decimal import Decimal

import pytest
from test_calculos_periodos import db
from test_reservas_aprobacion import crear, aprobar
from app.modules.vacaciones.saldos import service


def generar(c, empleado=2, **datos):
    return c.post(f'/saldos/{empleado}/periodos', json={'id_responsable': 2, **datos})


def test_primer_anio_y_repeticion(db):
    c, q, _ = db
    r = generar(c)
    assert r.status_code == 200, r.text
    resumen = r.json()['resumen']
    assert Decimal(resumen['total_disponible']) == 0
    assert Decimal(resumen['total_anticipable']) == 15
    assert len(r.json()['periodos_creados']) == 1
    assert q('SELECT fecha_inicio_periodo,fecha_fin_periodo,fecha_acreditacion FROM vacaciones.saldos WHERE id_empleado=2') == [('2026-02-01', '2027-01-31', '2027-02-01')]
    antes = q('SELECT * FROM vacaciones.saldos')
    assert generar(c).json()['periodos_creados'] == []
    assert q('SELECT * FROM vacaciones.saldos') == antes
    assert crear(c, empleado=2).status_code == 201


def test_no_reconstruye_historia_sin_fecha_explicita(db):
    c, q, e = db
    e("UPDATE core.empleados SET fecha_ingreso='2000-01-15' WHERE id_empleado=2")
    r = generar(c)
    assert r.status_code == 200
    assert q('SELECT fecha_inicio_periodo,dias_asignados FROM vacaciones.saldos WHERE id_empleado=2') == [('2026-01-15', 30)]
    assert Decimal(r.json()['resumen']['total_anticipable']) == 15


def test_recuperacion_explicita_y_sexto_anio(db):
    c, q, e = db
    e("UPDATE core.empleados SET fecha_ingreso='2020-10-27' WHERE id_empleado=2")
    r = generar(c, fecha_desde='2020-10-27')
    assert r.status_code == 200, r.text
    assert len(r.json()['periodos_creados']) == 7
    assert q('SELECT dias_asignados FROM vacaciones.saldos WHERE id_empleado=2 ORDER BY fecha_inicio_periodo') == [(15,), (15,), (15,), (15,), (15,), (16,), (17,)]
    assert Decimal(r.json()['resumen']['total_disponible']) == 91
    assert Decimal(r.json()['resumen']['total_anticipable']) == 15
    assert generar(c, fecha_desde='2020-10-27').json()['periodos_creados'] == []


def test_aniversario_conserva_anticipos_y_reservas(db, monkeypatch):
    c, q, _ = db
    assert generar(c).status_code == 200
    assert crear(c, empleado=2).status_code == 201
    assert aprobar(c).status_code == 201
    assert crear(c, '2026-12-01', '2026-12-03', empleado=2).status_code == 201
    saldo_antes = q('SELECT * FROM vacaciones.saldos WHERE id_empleado=2')
    reservas_antes = q('SELECT * FROM vacaciones.reservas_por_periodo')
    descuentos_antes = q('SELECT * FROM vacaciones.descuentos_por_periodo')
    monkeypatch.setattr(service, 'fecha_actual', lambda: date(2027, 2, 1))
    r = generar(c)
    assert r.status_code == 200, r.text
    assert len(r.json()['periodos_creados']) == 1
    assert q('SELECT * FROM vacaciones.saldos WHERE id_empleado=2 ORDER BY id_saldo')[0] == saldo_antes[0]
    assert q('SELECT * FROM vacaciones.reservas_por_periodo') == reservas_antes
    assert q('SELECT * FROM vacaciones.descuentos_por_periodo') == descuentos_antes
    assert Decimal(r.json()['resumen']['total_disponible']) == 7
    assert Decimal(r.json()['resumen']['total_reservado']) == 3
    assert Decimal(r.json()['resumen']['total_anticipable']) == 15
    assert generar(c).json()['periodos_creados'] == []


def test_continua_desde_ultimo_saldo_sin_reiniciar_cantidades(db, monkeypatch):
    c, q, e = db
    e('UPDATE vacaciones.saldos SET dias_asignados=25,dias_utilizados=20,dias_disponibles=5 WHERE id_saldo=20')
    antes = q('SELECT * FROM vacaciones.saldos ORDER BY id_saldo')
    monkeypatch.setattr(service, 'fecha_actual', lambda: date(2028, 11, 15))
    r = generar(c, empleado=1)
    assert r.status_code == 200, r.text
    assert len(r.json()['periodos_creados']) == 3
    assert q('SELECT * FROM vacaciones.saldos WHERE id_saldo IN (10,20,30) ORDER BY id_saldo') == antes
    assert q('SELECT dias_asignados FROM vacaciones.saldos WHERE id_empleado=1 ORDER BY fecha_inicio_periodo') == [(25,), (15,), (15,), (15,), (15,), (16,)]


def test_ingreso_bisiesto_recupera_el_29(db, monkeypatch):
    c, q, e = db
    e("UPDATE core.empleados SET fecha_ingreso='2024-02-29' WHERE id_empleado=2")
    monkeypatch.setattr(service, 'fecha_actual', lambda: date(2028, 2, 28))
    r = generar(c, fecha_desde='2024-02-29')
    assert r.status_code == 200, r.text
    assert len(r.json()['periodos_creados']) == 4
    assert q('SELECT fecha_inicio_periodo,fecha_fin_periodo,fecha_acreditacion FROM vacaciones.saldos WHERE id_empleado=2 ORDER BY fecha_inicio_periodo') == [
        ('2024-02-29', '2025-02-27', '2025-02-28'),
        ('2025-02-28', '2026-02-27', '2026-02-28'),
        ('2026-02-28', '2027-02-27', '2027-02-28'),
        ('2027-02-28', '2028-02-28', '2028-02-29'),
    ]
    monkeypatch.setattr(service, 'fecha_actual', lambda: date(2028, 2, 29))
    assert len(generar(c).json()['periodos_creados']) == 1
    assert q('SELECT fecha_acreditacion FROM vacaciones.saldos WHERE id_empleado=2 ORDER BY fecha_inicio_periodo DESC LIMIT 1') == [('2029-02-28',)]


@pytest.mark.parametrize('cambio', [
    'fecha_ingreso=NULL', "fecha_ingreso='2030-01-01'", 'estado=FALSE', 'estado=NULL',
])
def test_empleado_incompleto_o_inactivo_no_genera(db, cambio):
    c, q, e = db
    e('UPDATE core.empleados SET ' + cambio + ' WHERE id_empleado=2')
    assert generar(c).status_code == 409
    assert q('SELECT count(*) FROM vacaciones.saldos WHERE id_empleado=2') == [(0,)]


@pytest.mark.parametrize('desde', ['2025-02-01', '2026-03-01', '2027-02-01'])
def test_fecha_desde_invalida(db, desde):
    c, q, _ = db
    assert generar(c, fecha_desde=desde).status_code == 422
    assert q('SELECT count(*) FROM vacaciones.saldos WHERE id_empleado=2') == [(0,)]


def test_responsable_y_empleado_invalidos(db):
    c, q, _ = db
    assert generar(c, id_responsable=1).status_code == 403
    assert generar(c, empleado=999).status_code == 404
    assert generar(c, id_responsable=0).status_code == 422
    assert generar(c, dias_asignados=30).status_code == 422
    assert q('SELECT count(*) FROM vacaciones.saldos WHERE id_empleado=2') == [(0,)]


@pytest.mark.parametrize('cambio', [
    'fecha_inicio_periodo=NULL', "fecha_acreditacion='2026-11-16'",
    "fecha_inicio_periodo='2025-11-16'", 'dias_disponibles=99',
])
def test_saldo_inconsistente_no_se_corrige_automaticamente(db, cambio):
    c, q, e = db
    e('UPDATE vacaciones.saldos SET ' + cambio + ' WHERE id_saldo=30')
    antes = q('SELECT * FROM vacaciones.saldos')
    assert generar(c, empleado=1).status_code == 409
    assert q('SELECT * FROM vacaciones.saldos') == antes


def test_cambio_fecha_ingreso_no_duplica_periodos(db):
    c, q, e = db
    e("UPDATE core.empleados SET fecha_ingreso='2023-12-15' WHERE id_empleado=1")
    antes = q('SELECT * FROM vacaciones.saldos')
    assert generar(c, empleado=1).status_code == 409
    assert q('SELECT * FROM vacaciones.saldos') == antes


def test_fallo_despues_de_insertar_revierte_todo(db, monkeypatch):
    c, q, e = db
    e("UPDATE core.empleados SET fecha_ingreso='2024-02-01' WHERE id_empleado=2")
    original = service.insertar_periodos
    async def fallar(sesion, saldos):
        await original(sesion, saldos)
        raise RuntimeError('Fallo simulado despues de insertar')
    monkeypatch.setattr(service, 'insertar_periodos', fallar)
    with pytest.raises(RuntimeError):
        generar(c, fecha_desde='2024-02-01')
    assert q('SELECT count(*) FROM vacaciones.saldos WHERE id_empleado=2') == [(0,)]
