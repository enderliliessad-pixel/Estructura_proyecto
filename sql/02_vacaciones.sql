-- Ejecutar conectado a gestion_vacaciones_itq, despues de las dependencias de Core.
-- Esquema inicial
-- No es una migracion: si las tablas ya existen, no ejecutar como actualizacion.
-- Ante error, ejecutar ROLLBACK antes de reintentar.
BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE SCHEMA IF NOT EXISTS vacaciones;

CREATE TABLE vacaciones.saldos (
    id_saldo BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT REFERENCES core.empleados(id_empleado),
    periodo VARCHAR(20),
    dias_asignados NUMERIC(6,2),
    dias_utilizados NUMERIC(6,2),
    dias_disponibles NUMERIC(6,2)
);

CREATE TABLE vacaciones.solicitudes (
    id_solicitud BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT REFERENCES core.empleados(id_empleado),
    tipo VARCHAR(100),
    fecha_inicio DATE,
    fecha_fin DATE,
    dias_solicitados NUMERIC(6,2),
    horas_solicitadas NUMERIC(6,2),
    motivo TEXT,
    estado VARCHAR(50),
    fecha_solicitud TIMESTAMP
);

CREATE TABLE vacaciones.feriados (
    id_feriado BIGSERIAL PRIMARY KEY,
    fecha DATE,
    descripcion VARCHAR(200),
    tipo VARCHAR(100),
    estado BOOLEAN
);

CREATE TABLE vacaciones.aprobaciones (
    id_aprobacion BIGSERIAL PRIMARY KEY,
    id_solicitud BIGINT REFERENCES vacaciones.solicitudes(id_solicitud),
    id_aprobador BIGINT REFERENCES core.empleados(id_empleado),
    fecha TIMESTAMP,
    decision VARCHAR(50),
    observacion TEXT
);

CREATE TABLE vacaciones.permisos (
    id_permiso BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT REFERENCES core.empleados(id_empleado),
    fecha DATE,
    hora_inicio TIME,
    hora_fin TIME,
    total_horas NUMERIC(5,2),
    motivo TEXT,
    estado VARCHAR(50)
);

COMMIT;
