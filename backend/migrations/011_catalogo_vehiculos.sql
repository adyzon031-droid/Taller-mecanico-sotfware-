-- Crea el catálogo mínimo de estatus requerido por marcas/modelos.
-- El esquema real consultado no contiene estatus ni vehiculos.
CREATE TABLE IF NOT EXISTS estatus (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(30) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_estatus_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO estatus (nombre) VALUES ('activo'), ('en espera'), ('inactivo')
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre);

CREATE TABLE IF NOT EXISTS marcas (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(60) NOT NULL,
  estatus_id BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_marcas_nombre (nombre),
  KEY ix_marcas_nombre (nombre),
  KEY ix_marcas_estatus_nombre (estatus_id, nombre),
  CONSTRAINT fk_marcas_estatus FOREIGN KEY (estatus_id) REFERENCES estatus(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS modelos (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  marca_id BIGINT UNSIGNED NOT NULL,
  nombre VARCHAR(80) NOT NULL,
  estatus_id BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_modelos_marca_nombre (marca_id, nombre),
  KEY ix_modelos_nombre (nombre),
  KEY ix_modelos_marca_nombre (marca_id, nombre),
  KEY ix_modelos_estatus_nombre (estatus_id, nombre),
  CONSTRAINT fk_modelos_marca FOREIGN KEY (marca_id) REFERENCES marcas(id),
  CONSTRAINT fk_modelos_estatus FOREIGN KEY (estatus_id) REFERENCES estatus(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
