-- Ejecutar conectado a gestion_vacaciones_itq.
-- Dependencias de Vacaciones tomadas de Base de Datos.txt.
-- Si Core ya esta instalado con estas tres tablas, omitir este archivo.
-- No es una migracion: no altera tablas existentes. Ante error, ejecutar ROLLBACK.
BEGIN;

CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE core.personas (
    id_persona BIGSERIAL PRIMARY KEY,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    apellidos VARCHAR(100),
    correo VARCHAR(150),
    telefono VARCHAR(20),
    fecha_nacimiento DATE,
    direccion TEXT,
    estado BOOLEAN
);

CREATE TABLE core.unidades (
    id_unidad BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(150),
    descripcion TEXT,
    estado BOOLEAN
);

CREATE TABLE core.empleados (
    id_empleado BIGSERIAL PRIMARY KEY,
    id_persona BIGINT REFERENCES core.personas(id_persona),
    id_unidad BIGINT REFERENCES core.unidades(id_unidad),
    codigo_empleado VARCHAR(50),
    cargo VARCHAR(100),
    fecha_ingreso DATE,
    estado BOOLEAN
);

COMMIT;
