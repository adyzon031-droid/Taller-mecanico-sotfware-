ALTER TABLE talleres
  ADD COLUMN IF NOT EXISTS razon_social VARCHAR(180) NULL,
  ADD COLUMN IF NOT EXISTS rfc CHAR(13) NULL,
  ADD COLUMN IF NOT EXISTS email_contacto VARCHAR(190) NULL,
  ADD COLUMN IF NOT EXISTS telefono VARCHAR(24) NULL,
  ADD COLUMN IF NOT EXISTS telefono_prefijo VARCHAR(4) NOT NULL DEFAULT '52',
  ADD COLUMN IF NOT EXISTS telefono_pais CHAR(2) NOT NULL DEFAULT 'MX',
  ADD COLUMN IF NOT EXISTS calle VARCHAR(180) NULL,
  ADD COLUMN IF NOT EXISTS numero_interior VARCHAR(30) NULL,
  ADD COLUMN IF NOT EXISTS colonia VARCHAR(120) NULL,
  ADD COLUMN IF NOT EXISTS municipio VARCHAR(120) NULL,
  ADD COLUMN IF NOT EXISTS estado VARCHAR(120) NULL,
  ADD COLUMN IF NOT EXISTS codigo_postal CHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS direccion_temporal_calle VARCHAR(180) NULL,
  ADD COLUMN IF NOT EXISTS direccion_temporal_numero_interior VARCHAR(30) NULL,
  ADD COLUMN IF NOT EXISTS direccion_temporal_colonia VARCHAR(120) NULL,
  ADD COLUMN IF NOT EXISTS direccion_temporal_municipio VARCHAR(120) NULL,
  ADD COLUMN IF NOT EXISTS direccion_temporal_estado VARCHAR(120) NULL,
  ADD COLUMN IF NOT EXISTS direccion_temporal_codigo_postal CHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS foto_ruta VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS activo TINYINT(1) NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS suspendido_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS suspendido_por BIGINT UNSIGNED NULL,
  ADD COLUMN IF NOT EXISTS motivo_suspension VARCHAR(500) NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_talleres_empresa_nombre ON talleres(empresa_id,nombre);
CREATE UNIQUE INDEX IF NOT EXISTS uq_talleres_empresa_razon_social ON talleres(empresa_id,razon_social);
CREATE UNIQUE INDEX IF NOT EXISTS uq_talleres_empresa_rfc ON talleres(empresa_id,rfc);
CREATE UNIQUE INDEX IF NOT EXISTS uq_talleres_empresa_email ON talleres(empresa_id,email_contacto);
CREATE INDEX IF NOT EXISTS idx_talleres_empresa_activo ON talleres(empresa_id,activo);
