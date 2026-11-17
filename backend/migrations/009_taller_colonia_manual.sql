-- Additive and re-runnable migration for catalog-exempt manual workshop addresses.
SET @schema_name = DATABASE();
SET @has_colonia_manual = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @schema_name AND TABLE_NAME = 'talleres' AND COLUMN_NAME = 'colonia_manual'
);
SET @ddl = IF(@has_colonia_manual = 0,
  'ALTER TABLE talleres ADD COLUMN colonia_manual TINYINT(1) NOT NULL DEFAULT 0',
  'SELECT 1');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_temporal_manual = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @schema_name AND TABLE_NAME = 'talleres' AND COLUMN_NAME = 'direccion_temporal_colonia_manual'
);
SET @ddl = IF(@has_temporal_manual = 0,
  'ALTER TABLE talleres ADD COLUMN direccion_temporal_colonia_manual TINYINT(1) NOT NULL DEFAULT 0',
  'SELECT 1');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;
