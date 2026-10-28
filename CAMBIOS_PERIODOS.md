# Cálculo de días y saldos por período

Esta entrega incorpora las reglas informadas por Talento Humano: se cuentan ambos extremos del intervalo y los fines de semana, se excluyen los feriados activos y se prevé el consumo de los saldos más antiguos primero. La previsión no reserva días, no aprueba solicitudes y no registra descuentos efectivos.

## Instalación en tu base existente

1. Conserva una copia de tu proyecto y de la base. Detén el servidor antes de reemplazar los archivos.
2. En DBeaver, conectado a la base de Vacaciones, ejecuta **únicamente** `sql/03_periodos_y_descuentos.sql`. No vuelvas a ejecutar los scripts 00, 01 o 02 sobre una base existente. En una base nueva, ejecuta 00, 01, 02 y después 03 según sus instrucciones.
3. El script añade tres fechas a `vacaciones.saldos`, crea `vacaciones.descuentos_por_periodo` e índices. No borra ni convierte los datos antiguos. Si ocurre un error, ejecuta `ROLLBACK` antes de corregirlo.
4. Completa las fechas reales de los saldos existentes en DBeaver. Las tres fechas se guardan juntas. No se deducen del identificador o de textos como `PRUEBA-2026`.
5. Copia los archivos cambiados indicados abajo e instala `python -m pip install -r requirements.txt`. Se añadió `tzdata` para que la zona horaria de Quito funcione también en Windows.
6. Inicia el servidor y abre `/docs`.

No se ejecutó la migración sobre tu PostgreSQL local. Antes de la migración, el modelo nuevo de saldos no podrá consultar las columnas añadidas.

## Fechas de cada saldo

- `fecha_inicio_periodo`: primer día del año de servicio al que corresponde la asignación.
- `fecha_fin_periodo`: último día de ese año de servicio, inclusive.
- `fecha_acreditacion`: día en que esos días se habilitan, conforme al aniversario de ingreso informado.

Ejemplo de referencia: ingreso el 15/11/2026, período 15/11/2026 al 14/11/2027, acreditación el 15/11/2027. No copies estas fechas a empleados con otros datos.

No se crean automáticamente asignaciones anuales: falta confirmar el cálculo por antigüedad. Si se registra un saldo con acreditación futura, la consulta lo separa y no lo incluye en el total disponible hasta esa fecha. Esta separación usa la fecha actual de Quito, no el inicio futuro de la solicitud. Falta confirmar el tratamiento de aniversarios del 29 de febrero.

El resumen exige cantidades completas y no negativas, `asignados - utilizados = disponibles`, fechas completas y períodos sin superposición. Ante datos antiguos incompletos devuelve 409 con una explicación; no inventa ni corrige saldos automáticamente. La consulta original por empleado sigue mostrando los registros, incluidas sus fechas pendientes.

## Rutas nuevas

Todas usan el prefijo `/api/v1/vacaciones`.

- `GET /calculos/dias?fecha_inicio=2026-11-06&fecha_fin=2026-11-08`: calcula 3 días (viernes a domingo) si no hay feriados activos registrados en esas fechas.
- `GET /saldos/1/resumen`: devuelve cada período, separa los que todavía no se acreditan y suma los acreditados.
- `GET /saldos/1/prevision?fecha_inicio=2026-11-09&fecha_fin=2026-11-13`: calcula días y propone su reparto entre períodos. Con 3 días anteriores y 15 actuales, sin feriados en el intervalo, propone 3 + 2 y deja 13 disponibles.

La previsión indica `dias_sin_cobertura` si faltan días. No concede anticipos ni toma saldos futuros. Es una fotografía orientativa; se deberá repetir el cálculo y bloquear los saldos en la transacción del descuento efectivo cuando ese flujo se implemente.

## Cambio en registro y edición de solicitudes

`fecha_fin` representa el **último día de ausencia**, no la reincorporación. Para salir un viernes y regresar el lunes, se registra el domingo como fecha final.

Ahora puedes omitir `dias_solicitados`: el servidor lo calcula. Si lo envías por compatibilidad, debe coincidir con el cálculo o la API devuelve 422.

Ejemplo para crear una solicitud (usa un empleado existente):

```json
{
  "id_empleado": 1,
  "fecha_inicio": "2026-11-06",
  "fecha_fin": "2026-11-08",
  "motivo": "Solicitud de prueba"
}
```

Para editar se envían fechas y motivo, sin `id_empleado`. Una solicitud compuesta solamente por feriados no se registra. El intervalo máximo admitido es de 9999 días para respetar la capacidad actual del campo numérico.

El cálculo toma fechas únicas de feriados activos: dos registros en la misma fecha excluyen solo un día. Se debe mantener completo el calendario aplicable al trabajador. No se implementó selección por ciudad/sede. Los cambios posteriores al calendario no recalculan solicitudes ya guardadas; editar una solicitud pendiente sí recalcula sus días.

## Tabla de descuentos

Cada fila de `descuentos_por_periodo` relaciona una solicitud con un saldo e indica los días tomados de ese período. Una solicitud puede tener varias filas, pero una sola por saldo. Las referencias compuestas garantizan que la solicitud y el saldo pertenezcan al mismo empleado; no permiten borrar un saldo o una solicitud referenciados.

La tabla queda vacía en esta etapa. No insertes descuentos manuales para simular aprobaciones: todavía no existe el flujo que actualiza el saldo y registra el descuento conjuntamente. Los reversos por cancelación/interrupción se diseñarán cuando Talento Humano confirme el procedimiento.

## Pendientes

Momento del descuento, asignación por antigüedad, anticipos, etapas y facultades de aprobación/rechazo, correcciones y reversos, permisos por horas y fecha límite de uso acumulado. El rechazo anterior sigue siendo una operación provisional que no admite decisiones previas; todavía no representa el flujo de tres o cuatro intervenciones. La integración de identidad y roles con Core sigue pendiente.

## Archivos de esta entrega

Modificados:
- `app/main.py` (registro del router de cálculos).
- `app/modules/vacaciones/feriados/repository.py`.
- `app/modules/vacaciones/saldos/model.py`, `schema.py`, `service.py`, `router.py`.
- `app/modules/vacaciones/solicitudes/schema.py`, `service.py`, `router.py`.
- `requirements.txt`.

Añadidos:
- `app/modules/vacaciones/calculos/` con `__init__.py`, `schema.py`, `service.py`, `router.py`.
- `sql/03_periodos_y_descuentos.sql`.
- `tests/test_calculos_periodos.py` y `requirements-dev.txt`.
- Esta guía.

Si añadiste comentarios en tu copia local, compara y combina los archivos modificados para conservarlos. No necesitas reemplazar `.env`, aprobaciones, permisos ni los scripts SQL anteriores.

## Verificación reproducible

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Las pruebas nuevas usan SQLite temporal, sin leer tu `.env` ni conectarse a tu base. Verifican calendario, feriados duplicados/inactivos, acreditación, orden por fechas, reparto entre períodos, saldos insuficientes, datos incompletos y creación/edición con días calculados. No validan la ejecución de la migración ni los bloqueos de PostgreSQL.
