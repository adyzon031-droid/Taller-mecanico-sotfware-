-- Contacto complementario 1:1 y opción de colonia fuera del catálogo.
ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS colonia_manual TINYINT(1) NOT NULL DEFAULT 0;

-- La unicidad telefónica incluye prefijo y número. Se conservan todas las filas.
DROP INDEX IF EXISTS uq_clientes_taller_telefono ON clientes;
DROP INDEX IF EXISTS uq_clientes_taller_celular ON clientes;
CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_taller_celular_pais
  ON clientes(taller_id,celular_prefijo,celular);

CREATE TABLE IF NOT EXISTS cliente_contactos (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  cliente_id BIGINT UNSIGNED NOT NULL,
  nombre VARCHAR(180) NOT NULL,
  telefono_personal_prefijo VARCHAR(4) NOT NULL DEFAULT '52',
  telefono_personal_pais CHAR(2) NOT NULL DEFAULT 'MX',
  telefono_personal VARCHAR(24) NULL,
  email VARCHAR(190) NULL,
  telefono_trabajo_prefijo VARCHAR(4) NULL,
  telefono_trabajo_pais CHAR(2) NULL,
  telefono_trabajo VARCHAR(24) NULL,
  email_trabajo VARCHAR(190) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_cliente_contactos_cliente (cliente_id),
  CONSTRAINT fk_cliente_contactos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migra solo el nombre previamente capturado; los demás campos quedan pendientes.
INSERT INTO cliente_contactos (cliente_id, nombre, telefono_personal, email)
SELECT id, contacto_alterno, NULL, NULL FROM clientes
WHERE contacto_alterno IS NOT NULL AND TRIM(contacto_alterno) <> ''
ON DUPLICATE KEY UPDATE nombre=IF(nombre='', VALUES(nombre), nombre);

-- Los clientes históricos deben completar los nuevos campos de contacto.
UPDATE clientes SET datos_por_completar=1
WHERE celular IS NULL OR celular='' OR email IS NULL OR email=''
   OR NOT EXISTS (SELECT 1 FROM cliente_contactos cc WHERE cc.cliente_id=clientes.id AND cc.telefono_personal IS NOT NULL AND cc.telefono_personal<>'' AND cc.email IS NOT NULL AND cc.email<>'');
