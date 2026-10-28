from pathlib import Path
import sys
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from app.main import crear_app
from app.core.database import obtener_sesion
from app.modules.diagnostico import router as diagnostico

@pytest.fixture
def cliente(monkeypatch):
    # No iniciamos el lifespan: estas pruebas no leen .env ni abren PostgreSQL.
    aplicacion = crear_app()
    sesion = object()
    async def obtener_sesion_prueba():
        yield sesion
    aplicacion.dependency_overrides[obtener_sesion] = obtener_sesion_prueba
    comprobar = AsyncMock(return_value=True)
    monkeypatch.setattr(diagnostico, 'comprobar_base_datos', comprobar)
    cliente = TestClient(aplicacion)
    yield cliente, comprobar, sesion
    cliente.close()


def test_estado_api_no_consulta_base(cliente):
    respuesta = cliente[0].get('/api/v1/vacaciones/estado')
    assert respuesta.status_code == 200
    assert respuesta.json()['estado'] == 'ok'
    cliente[1].assert_not_awaited()


def test_estado_base_disponible(cliente):
    respuesta = cliente[0].get('/api/v1/vacaciones/estado/bd')
    assert respuesta.status_code == 200
    cliente[1].assert_awaited_once_with(cliente[2])


def test_estado_base_no_disponible(cliente):
    cliente[1].return_value = False
    assert cliente[0].get('/api/v1/vacaciones/estado/bd').status_code == 503


@pytest.mark.parametrize('error', [SQLAlchemyError('detalle interno'), OSError('detalle interno'), TimeoutError('detalle interno')])
def test_error_base_no_expone_detalles(cliente, error):
    cliente[1].side_effect = error
    respuesta = cliente[0].get('/api/v1/vacaciones/estado/bd')
    assert respuesta.status_code == 503
    assert 'detalle interno' not in respuesta.text
