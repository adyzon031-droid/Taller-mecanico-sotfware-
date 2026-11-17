-- Relaciones históricas de vehículos, VIN por taller y auditoría inmutable.
-- MariaDB 11; repetible y no destructiva.
DELIMITER //
DROP PROCEDURE IF EXISTS migration_013_relaciones_vehiculos//
CREATE PROCEDURE migration_013_relaciones_vehiculos()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vehiculos' AND COLUMN_NAME='excepcion_auditada') THEN
    ALTER TABLE vehiculos ADD COLUMN excepcion_auditada TINYINT(1) NOT NULL DEFAULT 0;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vehiculos' AND INDEX_NAME='uq_vehiculos_placa_vigente') THEN
    ALTER TABLE vehiculos DROP INDEX uq_vehiculos_placa_vigente;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vehiculos' AND INDEX_NAME='uq_vehiculos_serie_vigente') THEN
    ALTER TABLE vehiculos DROP INDEX uq_vehiculos_serie_vigente;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vehiculos' AND COLUMN_NAME='vin_unico_activo') THEN
    ALTER TABLE vehiculos ADD COLUMN vin_unico_activo CHAR(17) GENERATED ALWAYS AS (serie_vigente) STORED;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vehiculos' AND INDEX_NAME='uq_vehiculos_taller_vin_activo') THEN
    ALTER TABLE vehiculos ADD UNIQUE KEY uq_vehiculos_taller_vin_activo(taller_id,vin_unico_activo);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vehiculos' AND INDEX_NAME='idx_vehiculos_taller_placa_vigente') THEN
    ALTER TABLE vehiculos ADD KEY idx_vehiculos_taller_placa_vigente(taller_id,placa_vigente);
  END IF;
  CREATE TABLE IF NOT EXISTS cliente_vehiculo (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    cliente_id BIGINT UNSIGNED NOT NULL,
    vehiculo_id BIGINT UNSIGNED NOT NULL,
    taller_id BIGINT UNSIGNED NOT NULL,
    tipo_relacion ENUM('propietario','conductor habitual','responsable de pago') NOT NULL,
    es_principal TINYINT(1) NOT NULL DEFAULT 0,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NULL,
    motivo VARCHAR(500) NULL,
    created_by BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cerrada_por BIGINT UNSIGNED NULL,
    cerrada_en DATETIME NULL,
    principal_vigente_valor BIGINT UNSIGNED NULL,
    principal_vigente BIGINT UNSIGNED GENERATED ALWAYS AS (principal_vigente_valor) STORED,
    relacion_vigente_valor VARCHAR(100) NULL,
    relacion_vigente VARCHAR(100) GENERATED ALWAYS AS (relacion_vigente_valor) STORED,
    UNIQUE KEY uq_cliente_vehiculo_vigente(relacion_vigente),
    UNIQUE KEY uq_cliente_vehiculo_principal(principal_vigente),
    KEY idx_cliente_vehiculo_cliente_vigencia(cliente_id,fecha_fin),
    KEY idx_cliente_vehiculo_vehiculo_vigencia(vehiculo_id,fecha_fin),
    CONSTRAINT fk_cliente_vehiculo_cliente FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cliente_vehiculo_vehiculo FOREIGN KEY(vehiculo_id) REFERENCES vehiculos(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cliente_vehiculo_taller FOREIGN KEY(taller_id) REFERENCES talleres(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cliente_vehiculo_created_by FOREIGN KEY(created_by) REFERENCES usuarios(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cliente_vehiculo_cerrada_por FOREIGN KEY(cerrada_por) REFERENCES usuarios(id) ON DELETE RESTRICT
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
  INSERT INTO cliente_vehiculo(cliente_id,vehiculo_id,taller_id,tipo_relacion,es_principal,fecha_inicio,created_by,principal_vigente_valor,relacion_vigente_valor)
    SELECT v.cliente_id,v.id,v.taller_id,'propietario',1,COALESCE(v.fecha_ingreso,DATE(v.created_at)),v.created_by,v.id,CONCAT(v.cliente_id,':',v.id,':propietario')
    FROM vehiculos v LEFT JOIN cliente_vehiculo cv ON cv.vehiculo_id=v.id AND cv.es_principal=1 AND cv.fecha_fin IS NULL
    WHERE cv.id IS NULL;
  CREATE TABLE IF NOT EXISTS auditoria (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    taller_id BIGINT UNSIGNED NOT NULL,
    usuario_id BIGINT UNSIGNED NOT NULL,
    entidad VARCHAR(60) NOT NULL,
    entidad_id BIGINT UNSIGNED NOT NULL,
    accion VARCHAR(80) NOT NULL,
    motivo VARCHAR(500) NULL,
    datos_antes JSON NULL,
    datos_despues JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_auditoria_entidad(entidad,entidad_id),
    KEY idx_auditoria_taller_fecha(taller_id,created_at),
    CONSTRAINT fk_auditoria_taller FOREIGN KEY(taller_id) REFERENCES talleres(id) ON DELETE RESTRICT,
    CONSTRAINT fk_auditoria_usuario FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE RESTRICT
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
END//
CALL migration_013_relaciones_vehiculos()//
DROP PROCEDURE migration_013_relaciones_vehiculos//
DROP TRIGGER IF EXISTS trg_cliente_vehiculo_no_delete//
CREATE TRIGGER trg_cliente_vehiculo_no_delete BEFORE DELETE ON cliente_vehiculo FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Las relaciones históricas no se eliminan'//
DROP TRIGGER IF EXISTS trg_auditoria_no_update//
CREATE TRIGGER trg_auditoria_no_update BEFORE UPDATE ON auditoria FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='La auditoría no se modifica'//
DROP TRIGGER IF EXISTS trg_auditoria_no_delete//
CREATE TRIGGER trg_auditoria_no_delete BEFORE DELETE ON auditoria FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='La auditoría no se elimina'//
DELIMITER ;
