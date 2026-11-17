-- Garantiza una placa vigente única por taller para vehículos activos.
-- Reversión manual: ALTER TABLE vehiculos DROP INDEX uq_vehiculos_taller_placa_vigente;
-- Ejecutar solo tras verificar que no existan duplicados de (taller_id, placa_vigente).
DELIMITER //
DROP PROCEDURE IF EXISTS migration_014_unicidad_placa_vehiculo_activo//
CREATE PROCEDURE migration_014_unicidad_placa_vehiculo_activo()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vehiculos'
      AND INDEX_NAME='uq_vehiculos_taller_placa_vigente'
  ) THEN
    ALTER TABLE vehiculos
      ADD UNIQUE KEY uq_vehiculos_taller_placa_vigente(taller_id, placa_vigente);
  END IF;
END//
CALL migration_014_unicidad_placa_vehiculo_activo()//
DROP PROCEDURE migration_014_unicidad_placa_vehiculo_activo//
DELIMITER ;
