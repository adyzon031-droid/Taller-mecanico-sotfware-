-- Fase 02: esquema multi-taller. Aplicar sobre la base definida en DB_NAME.
CREATE TABLE IF NOT EXISTS empresas (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(160) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS talleres (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  empresa_id BIGINT UNSIGNED NOT NULL,
  nombre VARCHAR(160) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_talleres_empresa (empresa_id),
  CONSTRAINT fk_talleres_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS clientes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  taller_id BIGINT UNSIGNED NOT NULL,
  nombre_completo VARCHAR(180) NOT NULL,
  contacto_alterno VARCHAR(180) NULL,
  edad SMALLINT UNSIGNED NOT NULL,
  fecha_nacimiento DATE NOT NULL,
  telefono_personal VARCHAR(24) NOT NULL,
  telefono_trabajo VARCHAR(24) NOT NULL,
  email VARCHAR(254) NOT NULL,
  email_trabajo VARCHAR(254) NULL,
  foto_ruta VARCHAR(500) NULL,
  calle VARCHAR(180) NOT NULL,
  colonia VARCHAR(120) NOT NULL,
  municipio VARCHAR(120) NOT NULL,
  estado VARCHAR(120) NOT NULL,
  codigo_postal CHAR(5) NOT NULL,
  creado_por BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_clientes_taller_email (taller_id, email),
  UNIQUE KEY uq_clientes_taller_telefono (taller_id, telefono_personal),
  UNIQUE KEY uq_clientes_taller_nombre_nacimiento (taller_id, nombre_completo, fecha_nacimiento),
  KEY idx_clientes_taller (taller_id),
  KEY idx_clientes_email (email),
  KEY idx_clientes_telefono (telefono_personal),
  CONSTRAINT fk_clientes_taller FOREIGN KEY (taller_id) REFERENCES talleres(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
