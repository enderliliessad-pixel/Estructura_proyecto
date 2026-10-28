# API de Vacaciones — ITQ Conecta

Backend de consultas desarrollado con FastAPI, SQLAlchemy y PostgreSQL.


## Requisitos e instalación

Utiliza Python 3.12 o posterior (en tu equipo, Python 3.13), PostgreSQL y DBeaver u otro cliente SQL. Abre la terminal en la raíz del proyecto `Estructura_proyecto`, donde se encuentran `app/`, este README y `requirements.txt`.

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En Linux o macOS, activa el entorno con `source .venv/bin/activate`. También puedes ejecutar su intérprete directamente sin activarlo: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` en Windows.


## Configuración

Si todavía no tienes `.env`, copia `.env.example` a `.env`. Conserva tu configuración si ya existe. Completa estas variables en el archivo de la raíz:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gestion_vacaciones_itq
DB_USER=postgres
DB_PASSWORD=CAMBIA_POR_TU_CONTRASENA_LOCAL
```

El `.env` no debe subirse al repositorio. No se usa `DATABASE_URL` en esta versión personal.

# Base existente

No vuelvas a ejecutar los scripts de creación 00, 01 o 02 sobre tus tablas existentes. Si tienes las cinco tablas de vacaciones y sus dependencias, aplica únicamente `sql/03_periodos_y_descuentos.sql` para incorporar las fechas de períodos y la tabla de descuentos. Conserva una copia de la base antes de migrar. Si el script falla, ejecuta `ROLLBACK` y revisa el error.

Esta corrección de diagnóstico, pruebas y documentación no requiere migraciones nuevas. Los saldos antiguos necesitan sus tres fechas reales para usar resumen y previsión; no se completan automáticamente.

## Arranque y diagnóstico

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Documentación: <http://127.0.0.1:8000/docs>.
- API disponible: `GET /api/v1/vacaciones/estado` (no consulta PostgreSQL).
- Base disponible: `GET /api/v1/vacaciones/estado/bd` (consulta `SELECT 1`; devuelve 503 si no responde).

El diagnóstico comprueba disponibilidad; no verifica todas las tablas ni constituye autenticación.

## Funciones disponibles

Todas las rutas usan el prefijo `/api/v1/vacaciones`.

| Operación | Ruta |
|---|---|
| Listar solicitudes por empleado | `GET /solicitudes/{id_empleado}` |
| Crear solicitud pendiente | `POST /solicitudes` |
| Consultar una solicitud | `GET /solicitudes/detalle/{id_solicitud}` |
| Editar una solicitud pendiente | `PUT /solicitudes/detalle/{id_solicitud}` |
| Cancelar conservando el registro | `PATCH /solicitudes/detalle/{id_solicitud}/cancelar` |
| Consultar decisiones | `GET /solicitudes/{id_solicitud}/aprobaciones` |
| Registrar rechazo provisional | `POST /solicitudes/{id_solicitud}/rechazo` |
| Consultar saldos | `GET /saldos/{id_empleado}` |
| Resumen por períodos | `GET /saldos/{id_empleado}/resumen` |
| Prever distribución de días | `GET /saldos/{id_empleado}/prevision` |
| Calcular días | `GET /calculos/dias` |
| Consultar feriados | `GET /feriados` y `GET /feriados/{id_feriado}` |
| Crear o editar feriado | `POST /feriados` y `PUT /feriados/{id_feriado}` |
| Activar o desactivar feriado | `PATCH /feriados/{id_feriado}/estado` |
| Consultar permisos | `GET /permisos/{id_empleado}` |

Cálculo y previsión reciben `fecha_inicio` y `fecha_fin` como parámetros de consulta. La fecha final es el último día de ausencia, no el de regreso. Se incluyen ambos extremos y fines de semana; se excluyen las fechas únicas de feriados activos registrados.

Al crear una solicitud puedes omitir `dias_solicitados`; si lo envías, debe coincidir con el cálculo. La previsión utiliza primero los períodos antiguos acreditados a la fecha actual, no reserva ni descuenta saldo y no autoriza anticipos. Consulta `CAMBIOS_PERIODOS.md` para el detalle de estas reglas.


## Pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Las pruebas de períodos usan SQLite en memoria. Las de diagnóstico sustituyen la consulta por respuestas controladas y verifican el registro real de sus rutas en la aplicación. No leen el `.env` 

Para comprobar el seguimiento de las pruebas:

```powershell
git ls-files tests
git status --short
```

Si no aparecen, agrégalas con `git add tests requirements-dev.txt`. Conserva ignoradas las cachés y los entornos virtuales.
