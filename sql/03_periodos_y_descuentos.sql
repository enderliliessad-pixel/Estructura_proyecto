-- Ejecutar en la base existente, después de 02_vacaciones.sql.
-- No volver a ejecutar 00, 01 ni 02 en una base ya creada.
-- Esta migración conserva los saldos y solicitudes existentes.
-- Ante un error ejecutar ROLLBACK; revisar antes de reintentar.
BEGIN;

ALTER TABLE vacaciones.saldos
    ADD COLUMN IF NOT EXISTS fecha_inicio_periodo DATE,
    ADD COLUMN IF NOT EXISTS fecha_fin_periodo DATE,
    ADD COLUMN IF NOT EXISTS fecha_acreditacion DATE;

-- NULL permite conservar los registros antiguos hasta completar fechas verificadas.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'vacaciones.saldos'::regclass AND conname = 'saldos_fechas_validas'
    ) THEN
        ALTER TABLE vacaciones.saldos ADD CONSTRAINT saldos_fechas_validas CHECK (
            (fecha_inicio_periodo IS NULL AND fecha_fin_periodo IS NULL AND fecha_acreditacion IS NULL)
            OR
            (fecha_inicio_periodo IS NOT NULL AND fecha_fin_periodo IS NOT NULL
             AND fecha_acreditacion IS NOT NULL AND fecha_fin_periodo >= fecha_inicio_periodo)
        );
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_saldos_empleado_periodo
    ON vacaciones.saldos (id_empleado, fecha_inicio_periodo, id_saldo);
CREATE INDEX IF NOT EXISTS idx_feriados_activos_fecha
    ON vacaciones.feriados (fecha) WHERE estado IS TRUE;

-- Las referencias compuestas garantizan que saldo y solicitud sean del mismo empleado.
CREATE UNIQUE INDEX IF NOT EXISTS uq_saldos_id_empleado
    ON vacaciones.saldos (id_saldo, id_empleado);
CREATE UNIQUE INDEX IF NOT EXISTS uq_solicitudes_id_empleado
    ON vacaciones.solicitudes (id_solicitud, id_empleado);

CREATE TABLE IF NOT EXISTS vacaciones.descuentos_por_periodo (
    id_descuento BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT NOT NULL,
    id_solicitud BIGINT NOT NULL,
    id_saldo BIGINT NOT NULL,
    dias_descontados NUMERIC(6,2) NOT NULL
        CHECK (dias_descontados > 0 AND dias_descontados <= 9999.99),
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_descuento_solicitud_empleado
        FOREIGN KEY (id_solicitud, id_empleado)
        REFERENCES vacaciones.solicitudes (id_solicitud, id_empleado) ON DELETE RESTRICT,
    CONSTRAINT fk_descuento_saldo_empleado
        FOREIGN KEY (id_saldo, id_empleado)
        REFERENCES vacaciones.saldos (id_saldo, id_empleado) ON DELETE RESTRICT,
    CONSTRAINT uq_descuento_solicitud_saldo UNIQUE (id_solicitud, id_saldo)
);
CREATE INDEX IF NOT EXISTS idx_descuentos_saldo
    ON vacaciones.descuentos_por_periodo (id_saldo, id_empleado);

COMMIT;

-- No rellenar fechas a partir del ID ni de textos como PRUEBA-2026.
-- La acreditación automática por aniversario y el registro de descuentos se implementarán
-- cuando se confirmen antigüedad, anticipos y momento del descuento efectivo.
