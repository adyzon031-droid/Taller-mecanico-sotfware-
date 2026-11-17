ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS telefono_personal_prefijo VARCHAR(4) NOT NULL DEFAULT '52';
ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS telefono_trabajo_prefijo VARCHAR(4) NOT NULL DEFAULT '52';
ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS telefono_personal_pais CHAR(2) NOT NULL DEFAULT 'MX';
ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS telefono_trabajo_pais CHAR(2) NOT NULL DEFAULT 'MX';

ALTER TABLE clientes
  ADD UNIQUE INDEX IF NOT EXISTS uq_clientes_taller_telefono_prefijo
  (taller_id, telefono_personal_prefijo, telefono_personal);
ALTER TABLE clientes
  DROP INDEX IF EXISTS uq_clientes_taller_telefono;
