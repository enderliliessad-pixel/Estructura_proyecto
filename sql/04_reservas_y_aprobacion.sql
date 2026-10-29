-- Ejecutar despues de 03_periodos_y_descuentos.sql con el servidor detenido.
-- Conserva los datos existentes. No descuenta ni reserva solicitudes antiguas.
-- Si falla una instruccion ejecutar ROLLBACK antes de corregir y reintentar.
BEGIN;

ALTER TABLE vacaciones.solicitudes
    ADD COLUMN IF NOT EXISTS reserva_gestionada BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE vacaciones.descuentos_por_periodo
    ADD COLUMN IF NOT EXISTS es_anticipo BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS vacaciones.reservas_por_periodo (
    id_reserva BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT NOT NULL,
    id_solicitud BIGINT NOT NULL,
    id_saldo BIGINT NOT NULL,
    dias_reservados NUMERIC(6,2) NOT NULL CHECK (dias_reservados > 0 AND dias_reservados <= 9999.99),
    es_anticipo BOOLEAN NOT NULL,
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('ACTIVA','LIBERADA','CONSUMIDA')),
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMPTZ,
    CONSTRAINT fk_reserva_solicitud_empleado FOREIGN KEY (id_solicitud,id_empleado)
        REFERENCES vacaciones.solicitudes(id_solicitud,id_empleado) ON DELETE RESTRICT,
    CONSTRAINT fk_reserva_saldo_empleado FOREIGN KEY (id_saldo,id_empleado)
        REFERENCES vacaciones.saldos(id_saldo,id_empleado) ON DELETE RESTRICT,
    CONSTRAINT reserva_cierre_coherente CHECK (
        (estado = 'ACTIVA' AND fecha_cierre IS NULL) OR
        (estado <> 'ACTIVA' AND fecha_cierre IS NOT NULL)
    )
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_solicitud_saldo
    ON vacaciones.reservas_por_periodo(id_solicitud,id_saldo) WHERE estado='ACTIVA';
CREATE INDEX IF NOT EXISTS idx_reservas_empleado_activas
    ON vacaciones.reservas_por_periodo(id_empleado,id_saldo) WHERE estado='ACTIVA';
CREATE INDEX IF NOT EXISTS idx_reservas_historial ON vacaciones.reservas_por_periodo(id_solicitud,id_reserva);
CREATE INDEX IF NOT EXISTS idx_reservas_saldo ON vacaciones.reservas_por_periodo(id_saldo,id_empleado);
CREATE INDEX IF NOT EXISTS idx_solicitudes_cruce
    ON vacaciones.solicitudes(id_empleado,fecha_inicio,fecha_fin)
    WHERE tipo='VACACIONES' AND estado IN ('PENDIENTE','APROBADA');

-- Habilitacion local explicita. No equivale a autenticar a quien realiza la peticion.
-- No se habilita automaticamente a nadie ni se infieren permisos del nombre del cargo.
CREATE TABLE IF NOT EXISTS vacaciones.responsables_talento_humano (
    id_empleado BIGINT PRIMARY KEY REFERENCES core.empleados(id_empleado) ON DELETE RESTRICT,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

-- NOT VALID conserva registros antiguos inconsistentes para su revision.
-- PostgreSQL si comprueba esta regla al insertar o actualizar un saldo.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid='vacaciones.saldos'::regclass AND conname='saldo_cantidades_coherentes') THEN
        ALTER TABLE vacaciones.saldos ADD CONSTRAINT saldo_cantidades_coherentes CHECK (
            dias_asignados IS NOT NULL AND dias_utilizados IS NOT NULL AND dias_disponibles IS NOT NULL
            AND dias_asignados BETWEEN 0 AND 9999.99
            AND dias_utilizados BETWEEN 0 AND 9999.99
            AND dias_disponibles BETWEEN 0 AND 9999.99
            AND dias_asignados - dias_utilizados = dias_disponibles
        ) NOT VALID;
    END IF;
END;
$$;
COMMIT;

-- Consultar y conciliar cada pendiente antiguo con POST /solicitudes/detalle/{id}/reserva.
-- Si existe un cruce o saldo insuficiente, revisar el documento antes de editar o cancelar.
SELECT id_solicitud,id_empleado,fecha_inicio,fecha_fin,dias_solicitados
FROM vacaciones.solicitudes
WHERE tipo='VACACIONES' AND estado='PENDIENTE' AND NOT reserva_gestionada
ORDER BY id_empleado,fecha_solicitud,id_solicitud;
