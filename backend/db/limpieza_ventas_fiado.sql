-- ============================================================================
-- LIMPIEZA ÚNICA — Eliminar del todo el fiado de una BD ya aprovisionada.
-- Base de datos: PostgreSQL 16.
--
-- Borra SOLO las ventas cuyo método de pago fue FIADO y todo lo que cuelga de
-- ellas. Las boletas y ventas de OTROS métodos (efectivo, yape, etc.) NO se
-- tocan. También retira las tablas del fiado (clientes/fiados/abonos) y la
-- columna ventas.cliente_id.
--
-- ORDEN (clave): las tablas fiados/abonos referencian a ventas
-- (fiados.venta_id, ON DELETE RESTRICT), así que se sueltan ANTES de borrar las
-- ventas; si no, Postgres bloquea el DELETE de ventas.
--
-- Transacción: o se aplica todo, o nada. Idempotente: re-ejecutar no hace daño
-- (la segunda vez el conjunto de ventas al fiado ya está vacío).
-- ============================================================================
BEGIN;

-- Ventas objetivo: las pagadas con FIADO. Se capturan los ids AHORA, antes de
-- cualquier borrado (después no habría cómo reconstruir el criterio).
CREATE TEMP TABLE _ventas_fiado ON COMMIT DROP AS
SELECT DISTINCT v.id
FROM ventas v
WHERE v.metodo_pago = 'FIADO'
   OR EXISTS (
       SELECT 1 FROM pagos_venta pv
       WHERE pv.venta_id = v.id AND pv.codigo_metodo = 'FIADO'
   );

-- 1. PRIMERO soltar las tablas del fiado: abonos referencia a fiados, y fiados
--    referencia a ventas (RESTRICT) — bloquearían el borrado de las ventas.
DROP TABLE IF EXISTS abonos CASCADE;
DROP TABLE IF EXISTS fiados CASCADE;

-- 2. Borrar lo que cuelga de esas ventas y que sí existe (Módulo D y anulaciones
--    pueden no estar en esta BD): boletas + sus archivos de Drive, y reversos.
DO $$
BEGIN
    IF to_regclass('archivos_drive') IS NOT NULL
       AND to_regclass('boletas_clientes') IS NOT NULL THEN
        DELETE FROM archivos_drive
        WHERE boleta_id IN (
            SELECT id FROM boletas_clientes
            WHERE venta_id IN (SELECT id FROM _ventas_fiado)
        );
    END IF;
    IF to_regclass('boletas_clientes') IS NOT NULL THEN
        DELETE FROM boletas_clientes
        WHERE venta_id IN (SELECT id FROM _ventas_fiado);
    END IF;
    IF to_regclass('anulaciones') IS NOT NULL THEN
        DELETE FROM anulaciones
        WHERE venta_id IN (SELECT id FROM _ventas_fiado);
    END IF;
END $$;

-- 3. Pagos y detalles de esas ventas (FK -> ventas).
DELETE FROM pagos_venta   WHERE venta_id IN (SELECT id FROM _ventas_fiado);
DELETE FROM detalles_venta WHERE venta_id IN (SELECT id FROM _ventas_fiado);

-- 4. Las ventas al fiado (ya sin fiados ni hijos que las referencien).
DELETE FROM ventas WHERE id IN (SELECT id FROM _ventas_fiado);

-- 5. La columna de enlace y la tabla de clientes.
ALTER TABLE IF EXISTS ventas DROP COLUMN IF EXISTS cliente_id;
DROP TABLE IF EXISTS clientes CASCADE;

-- 6. El método FIADO, ya sin ninguna venta que lo referencie.
DELETE FROM metodos_pago WHERE codigo = 'FIADO';

COMMIT;
