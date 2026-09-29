-- Cuentas necesarias para que el login establezca la sesión exigida por Fase 02.
CREATE TABLE IF NOT EXISTS usuarios (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  taller_id BIGINT UNSIGNED NOT NULL,
  nombre VARCHAR(180) NOT NULL,
  email VARCHAR(254) NOT NULL,
  password_hash VARCHAR(60) NOT NULL,
  rol ENUM('administrador','recepcionista','secretaria','gerente','tecnico','cliente') NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_usuarios_email (email),
  KEY idx_usuarios_taller_rol (taller_id, rol),
  CONSTRAINT fk_usuarios_taller FOREIGN KEY (taller_id) REFERENCES talleres(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
