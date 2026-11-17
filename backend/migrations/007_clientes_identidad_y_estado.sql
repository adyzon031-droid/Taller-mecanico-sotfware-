ALTER TABLE clientes MODIFY COLUMN telefono_trabajo VARCHAR(24) NULL;
ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS nombres VARCHAR(180) NULL,
  ADD COLUMN IF NOT EXISTS apellido_paterno VARCHAR(100) NULL,
  ADD COLUMN IF NOT EXISTS apellido_materno VARCHAR(100) NULL,
  ADD COLUMN IF NOT EXISTS datos_por_completar TINYINT(1) NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS curp CHAR(18) NULL,
  ADD COLUMN IF NOT EXISTS rfc CHAR(13) NULL,
  ADD COLUMN IF NOT EXISTS celular VARCHAR(24) NULL,
  ADD COLUMN IF NOT EXISTS celular_prefijo VARCHAR(4) NOT NULL DEFAULT '52',
  ADD COLUMN IF NOT EXISTS celular_pais CHAR(2) NOT NULL DEFAULT 'MX',
  ADD COLUMN IF NOT EXISTS telefono_fijo VARCHAR(24) NULL,
  ADD COLUMN IF NOT EXISTS telefono_fijo_prefijo VARCHAR(4) NOT NULL DEFAULT '52',
  ADD COLUMN IF NOT EXISTS telefono_fijo_pais CHAR(2) NOT NULL DEFAULT 'MX',
  ADD COLUMN IF NOT EXISTS telefono_trabajo_pais CHAR(2) NOT NULL DEFAULT 'MX',
  ADD COLUMN IF NOT EXISTS numero_interior VARCHAR(30) NULL,
  ADD COLUMN IF NOT EXISTS estado_cliente ENUM('activo','suspendido') NOT NULL DEFAULT 'activo',
  ADD COLUMN IF NOT EXISTS suspendido_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS suspendido_por BIGINT UNSIGNED NULL,
  ADD COLUMN IF NOT EXISTS motivo_suspension VARCHAR(500) NULL;
UPDATE clientes SET nombres=nombre_completo, celular=telefono_personal,
  celular_prefijo=telefono_personal_prefijo, celular_pais=telefono_personal_pais,
  datos_por_completar=1 WHERE nombres IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_taller_curp ON clientes(taller_id,curp);
CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_taller_rfc ON clientes(taller_id,rfc);
CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_taller_celular ON clientes(taller_id,celular_prefijo,celular);
CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_taller_nombres_apellidos_fecha
  ON clientes(taller_id,nombres,apellido_paterno,apellido_materno,fecha_nacimiento);
CREATE INDEX IF NOT EXISTS idx_clientes_estado ON clientes(taller_id,estado_cliente,activo);
