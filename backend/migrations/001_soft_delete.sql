-- =====================================================================
-- Migración 001: Borrado lógico (soft delete)
--
-- Agrega las columnas de control de borrado a las tablas que se
-- limpian al iniciar un nuevo ciclo. Ninguna fila se borra físicamente:
-- se marca eliminado = 1 y se guarda la fecha y quién la borró.
--
-- Ejecutar UNA sola vez sobre la base de datos de producción.
-- Es idempotente: si la columna ya existe, MySQL avisa con un error
-- 1060 (Duplicate column name) que se puede ignorar sin riesgo.
-- =====================================================================

-- ------------------------- grupo -------------------------
ALTER TABLE grupo
    ADD COLUMN eliminado TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN fecha_eliminado DATETIME NULL DEFAULT NULL,
    ADD COLUMN eliminado_por VARCHAR(100) NULL DEFAULT NULL;

CREATE INDEX idx_grupo_eliminado ON grupo (eliminado);

-- ----------------------- estudiante ----------------------
ALTER TABLE estudiante
    ADD COLUMN eliminado TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN fecha_eliminado DATETIME NULL DEFAULT NULL,
    ADD COLUMN eliminado_por VARCHAR(100) NULL DEFAULT NULL;

-- Índice compuesto: casi todas las consultas filtran por grupo + eliminado
CREATE INDEX idx_estudiante_eliminado ON estudiante (eliminado);
CREATE INDEX idx_estudiante_grupo_eliminado ON estudiante (id_grupo, eliminado);

-- ------------------------- clase -------------------------
ALTER TABLE clase
    ADD COLUMN eliminado TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN fecha_eliminado DATETIME NULL DEFAULT NULL,
    ADD COLUMN eliminado_por VARCHAR(100) NULL DEFAULT NULL;

CREATE INDEX idx_clase_eliminado ON clase (eliminado);
CREATE INDEX idx_clase_grupo_eliminado ON clase (id_grupo, eliminado);

-- --------------------- horario_clase ---------------------
ALTER TABLE horario_clase
    ADD COLUMN eliminado TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN fecha_eliminado DATETIME NULL DEFAULT NULL,
    ADD COLUMN eliminado_por VARCHAR(100) NULL DEFAULT NULL;

CREATE INDEX idx_horario_eliminado ON horario_clase (eliminado);

-- =====================================================================
-- Verificación: estas consultas deben devolver 0 filas eliminadas
-- recién aplicada la migración.
-- =====================================================================
-- SELECT COUNT(*) AS grupos_eliminados      FROM grupo         WHERE eliminado = 1;
-- SELECT COUNT(*) AS alumnos_eliminados     FROM estudiante    WHERE eliminado = 1;
-- SELECT COUNT(*) AS clases_eliminadas      FROM clase         WHERE eliminado = 1;
-- SELECT COUNT(*) AS horarios_eliminados    FROM horario_clase WHERE eliminado = 1;
