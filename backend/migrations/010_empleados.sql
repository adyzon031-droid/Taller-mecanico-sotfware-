-- Empleados y rol mecánico, aditivo e idempotente.
ALTER TABLE usuarios MODIFY rol ENUM('administrador','recepcionista','mecanico') NOT NULL;

CREATE TABLE IF NOT EXISTS empleados (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
 taller_id BIGINT UNSIGNED NOT NULL,
 usuario_id BIGINT UNSIGNED NOT NULL,
 nombres VARCHAR(120) NULL,
 apellido_paterno VARCHAR(80) NULL,
 apellido_materno VARCHAR(80) NULL,
 curp CHAR(18) NULL,
 rfc CHAR(13) NULL,
 fecha_nacimiento DATE NULL,
 telefono_personal VARCHAR(24) NULL,
 telefono_personal_prefijo VARCHAR(4) NULL,
 telefono_personal_pais CHAR(2) NULL,
 email VARCHAR(190) NULL,
 telefono_trabajo VARCHAR(24) NULL,
 telefono_trabajo_prefijo VARCHAR(4) NULL,
 telefono_trabajo_pais CHAR(2) NULL,
 email_trabajo VARCHAR(190) NULL,
 calle VARCHAR(180) NULL,
 numero_interior VARCHAR(30) NULL,
 codigo_postal CHAR(5) NULL,
 estado VARCHAR(120) NULL,
 municipio VARCHAR(120) NULL,
 colonia VARCHAR(120) NULL,
 colonia_manual TINYINT(1) NOT NULL DEFAULT 0,
 contacto_emergencia_nombre VARCHAR(160) NULL,
 contacto_emergencia_parentesco VARCHAR(80) NULL,
 contacto_emergencia_telefono VARCHAR(24) NULL,
 contacto_emergencia_prefijo VARCHAR(4) NULL,
 contacto_emergencia_pais CHAR(2) NULL,
 puesto VARCHAR(120) NULL,
 fecha_ingreso DATE NULL,
 foto_ruta VARCHAR(500) NULL,
 activo TINYINT(1) NOT NULL DEFAULT 1,
 fecha_baja DATETIME NULL,
 motivo_baja VARCHAR(500) NULL,
 baja_por BIGINT UNSIGNED NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 PRIMARY KEY (id), UNIQUE KEY uq_empleados_usuario (usuario_id),
 KEY ix_empleados_taller_activo (taller_id,activo), KEY ix_empleados_curp (curp), KEY ix_empleados_rfc (rfc),
 CONSTRAINT fk_empleados_taller FOREIGN KEY (taller_id) REFERENCES talleres(id),
 CONSTRAINT fk_empleados_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
 CONSTRAINT fk_empleados_baja_usuario FOREIGN KEY (baja_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO empleados (taller_id,usuario_id,nombres,email,activo)
 SELECT taller_id,id,nombre,email,activo FROM usuarios;

ALTER TABLE empleados ADD COLUMN IF NOT EXISTS empresa_id BIGINT UNSIGNED NULL AFTER id;
UPDATE empleados e JOIN talleres t ON t.id=e.taller_id SET e.empresa_id=t.empresa_id WHERE e.empresa_id IS NULL;
ALTER TABLE empleados MODIFY empresa_id BIGINT UNSIGNED NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_empleados_empresa_curp ON empleados(empresa_id,curp);
CREATE UNIQUE INDEX IF NOT EXISTS uq_empleados_empresa_rfc ON empleados(empresa_id,rfc);
CREATE UNIQUE INDEX IF NOT EXISTS uq_empleados_empresa_email ON empleados(empresa_id,email);
CREATE UNIQUE INDEX IF NOT EXISTS uq_empleados_empresa_telefono ON empleados(empresa_id,telefono_personal);
