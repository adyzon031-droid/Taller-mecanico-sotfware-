-- Extiende estatus y agrega estado normalizado para clientes y vehículos.
-- Compatible con MariaDB 11; no elimina filas y puede ejecutarse más de una vez.
DELIMITER //
DROP PROCEDURE IF EXISTS migration_012_estatus_vehiculos//
CREATE PROCEDURE migration_012_estatus_vehiculos()
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='estatus' AND COLUMN_NAME='nombre')
     AND NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='estatus' AND COLUMN_NAME='valor') THEN
    ALTER TABLE estatus CHANGE COLUMN nombre valor VARCHAR(30) NOT NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='estatus' AND COLUMN_NAME='descripcion') THEN
    ALTER TABLE estatus ADD COLUMN descripcion VARCHAR(255) NOT NULL DEFAULT '';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='estatus' AND COLUMN_NAME='es_sistema') THEN
    ALTER TABLE estatus ADD COLUMN es_sistema TINYINT(1) NOT NULL DEFAULT 0;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='estatus' AND COLUMN_NAME='activo') THEN
    ALTER TABLE estatus ADD COLUMN activo TINYINT(1) NOT NULL DEFAULT 1;
  END IF;
  UPDATE estatus SET valor=LOWER(TRIM(valor)), descripcion=CASE LOWER(TRIM(valor))
    WHEN 'activo' THEN 'Registro habilitado para las operaciones normales del sistema.'
    WHEN 'en espera' THEN 'Registro pendiente de revisión y aprobación administrativa.'
    WHEN 'inactivo' THEN 'Registro deshabilitado temporalmente del catálogo.'
    WHEN 'suspendido' THEN 'Registro suspendido temporalmente y no disponible para operaciones.'
    WHEN 'cancelado' THEN 'Registro cuya operación fue cancelada.'
    WHEN 'eliminado' THEN 'Registro dado de baja de forma lógica y conservado para auditoría.'
    WHEN 'actualizado' THEN 'Registro que fue actualizado y conserva su historial.'
    ELSE descripcion END
    WHERE descripcion='';
  INSERT INTO estatus(valor,descripcion,es_sistema,activo)
    SELECT 'suspendido','Registro suspendido temporalmente y no disponible para operaciones.',1,1
    WHERE NOT EXISTS(SELECT 1 FROM estatus WHERE valor='suspendido');
  INSERT INTO estatus(valor,descripcion,es_sistema,activo)
    SELECT 'cancelado','Registro cuya operación fue cancelada.',0,1
    WHERE NOT EXISTS(SELECT 1 FROM estatus WHERE valor='cancelado');
  INSERT INTO estatus(valor,descripcion,es_sistema,activo)
    SELECT 'eliminado','Registro dado de baja de forma lógica y conservado para auditoría.',1,1
    WHERE NOT EXISTS(SELECT 1 FROM estatus WHERE valor='eliminado');
  INSERT INTO estatus(valor,descripcion,es_sistema,activo)
    SELECT 'actualizado','Registro que fue actualizado y conserva su historial.',0,1
    WHERE NOT EXISTS(SELECT 1 FROM estatus WHERE valor='actualizado');
  UPDATE estatus SET es_sistema=1 WHERE valor IN ('activo','en espera','inactivo','suspendido','eliminado');
  UPDATE estatus SET es_sistema=0 WHERE valor IN ('cancelado','actualizado');
  IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='clientes' AND COLUMN_NAME='estatus_id') THEN
    ALTER TABLE clientes ADD COLUMN estatus_id BIGINT UNSIGNED NULL;
  END IF;
  UPDATE clientes c JOIN estatus e ON e.valor=CASE WHEN c.deleted_at IS NOT NULL OR c.activo=0 THEN 'eliminado' WHEN c.estado_cliente='suspendido' THEN 'suspendido' ELSE 'activo' END SET c.estatus_id=e.id WHERE c.estatus_id IS NULL;
  IF NOT EXISTS (SELECT 1 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='clientes' AND INDEX_NAME='idx_clientes_taller_estatus') THEN
    ALTER TABLE clientes ADD INDEX idx_clientes_taller_estatus(taller_id,estatus_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() AND TABLE_NAME='clientes' AND CONSTRAINT_NAME='fk_clientes_estatus') THEN
    ALTER TABLE clientes ADD CONSTRAINT fk_clientes_estatus FOREIGN KEY(estatus_id) REFERENCES estatus(id);
  END IF;
  ALTER TABLE clientes MODIFY estatus_id BIGINT UNSIGNED NOT NULL;
  CREATE TABLE IF NOT EXISTS vehiculos (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    cliente_id BIGINT UNSIGNED NOT NULL,
    taller_id BIGINT UNSIGNED NOT NULL,
    placa VARCHAR(8) NOT NULL,
    marca_id BIGINT UNSIGNED NULL,
    modelo_id BIGINT UNSIGNED NULL,
    marca_texto VARCHAR(60) NOT NULL,
    modelo_texto VARCHAR(80) NULL,
    anio SMALLINT UNSIGNED NOT NULL,
    version VARCHAR(40) NULL,
    numero_serie CHAR(17) NULL,
    kilometraje INT UNSIGNED NULL,
    fecha_ingreso DATE NOT NULL,
    estatus_id BIGINT UNSIGNED NOT NULL,
    created_by BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    deleted_by BIGINT UNSIGNED NULL,
    -- Campos nulos al dar de baja; índices únicos permiten reutilizar valores.
    placa_vigente VARCHAR(8) NULL,
    serie_vigente CHAR(17) NULL,
    UNIQUE KEY uq_vehiculos_placa_vigente(placa_vigente),
    UNIQUE KEY uq_vehiculos_serie_vigente(serie_vigente),
    KEY idx_vehiculos_taller_estatus(taller_id,estatus_id),
    KEY idx_vehiculos_cliente(cliente_id), KEY idx_vehiculos_marca(marca_id), KEY idx_vehiculos_modelo(modelo_id),
    KEY idx_vehiculos_serie(numero_serie),
    CONSTRAINT fk_vehiculos_cliente FOREIGN KEY(cliente_id) REFERENCES clientes(id),
    CONSTRAINT fk_vehiculos_taller FOREIGN KEY(taller_id) REFERENCES talleres(id),
    CONSTRAINT fk_vehiculos_marca FOREIGN KEY(marca_id) REFERENCES marcas(id),
    CONSTRAINT fk_vehiculos_modelo FOREIGN KEY(modelo_id) REFERENCES modelos(id),
    CONSTRAINT fk_vehiculos_estatus FOREIGN KEY(estatus_id) REFERENCES estatus(id),
    CONSTRAINT fk_vehiculos_created_by FOREIGN KEY(created_by) REFERENCES usuarios(id),
    CONSTRAINT fk_vehiculos_deleted_by FOREIGN KEY(deleted_by) REFERENCES usuarios(id)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
END//
CALL migration_012_estatus_vehiculos()//
DROP PROCEDURE migration_012_estatus_vehiculos//
DELIMITER ;
