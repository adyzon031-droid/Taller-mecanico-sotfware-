CREATE TABLE IF NOT EXISTS codigos_postales (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  cp CHAR(5) NOT NULL,
  estado VARCHAR(120) NOT NULL,
  municipio VARCHAR(120) NOT NULL,
  colonia VARCHAR(180) NOT NULL,
  tipo_asentamiento VARCHAR(100) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_codigos_postales_cp (cp),
  KEY idx_codigos_postales_localidad (estado, municipio, colonia),
  UNIQUE KEY uq_codigos_postales_fila (cp, estado, municipio, colonia, tipo_asentamiento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
