-- Baja lógica para clientes. Idempotente en MariaDB; los registros existentes
-- conservan sus datos y reciben activo=1 por el valor DEFAULT.
ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS activo TINYINT(1) NOT NULL DEFAULT 1;

ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS deleted_at DATETIME NULL DEFAULT NULL;
