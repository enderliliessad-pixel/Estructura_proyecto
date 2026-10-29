-- Ejecutar despues de 04, con el servidor detenido y una copia de respaldo.
-- No crea tablas ni modifica saldos. Ante error ejecutar ROLLBACK.
BEGIN;

-- No elegimos automaticamente que saldo conservar si existen duplicados o cruces.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM vacaciones.saldos a
        JOIN vacaciones.saldos b ON a.id_empleado = b.id_empleado
            AND a.id_saldo < b.id_saldo
            AND a.fecha_inicio_periodo <= b.fecha_fin_periodo
            AND b.fecha_inicio_periodo <= a.fecha_fin_periodo
    ) THEN
        RAISE EXCEPTION 'Hay periodos de saldo superpuestos. Revisarlos antes de aplicar 05; no se modificaron datos.';
    END IF;
END;
$$;

-- La clave usa la fecha real, no el texto del periodo. Los NULL antiguos se conservan.
CREATE UNIQUE INDEX IF NOT EXISTS uq_saldos_empleado_inicio
    ON vacaciones.saldos (id_empleado, fecha_inicio_periodo);

COMMIT;
