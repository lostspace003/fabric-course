-- Demo 2.4 - Fabric Data Warehouse: cross-database query on the lakehouse + CTAS.
-- Run in the warehouse's SQL query editor (ws-fabric-tour). ⟲ verify at recording: menu names and the "+ Warehouses" button.
--
-- Setup in the UI before running:
--   1. In the warehouse editor's object Explorer, select "+ Warehouses" and add lh_reference (its SQL analytics endpoint). ⟲ verify
--   2. Three-part names are <item>.<schema>.<table>; lakehouse tables live in schema dbo.
--   The sample_orders table is Lab 2.8/2.9's orders_sample.csv loaded into lh_reference.

-- ---------------------------------------------------------------------------------------------
-- 1. Cross-database query: late rate by carrier, reading lakehouse tables through the SQL analytics endpoint.
--    Nothing is copied: the warehouse reads the lakehouse's Delta tables in place.
SELECT c.carrier_name,
       COUNT(*)                                   AS orders,
       SUM(CAST(o.is_late AS INT))                AS late_orders,
       CAST(AVG(CAST(o.is_late AS FLOAT)) AS DECIMAL(5,3)) AS late_rate
FROM lh_reference.dbo.sample_orders AS o
JOIN lh_reference.dbo.ref_carriers  AS c ON c.carrier_id = o.carrier_id
GROUP BY c.carrier_name
ORDER BY late_rate DESC;

-- 2. Same idea, two joins: carrier x remoteness (the cell the model must learn).
SELECT c.carrier_name, r.remoteness,
       COUNT(*) AS orders,
       CAST(AVG(CAST(o.is_late AS FLOAT)) AS DECIMAL(5,3)) AS late_rate
FROM lh_reference.dbo.sample_orders AS o
JOIN lh_reference.dbo.ref_carriers  AS c ON c.carrier_id = o.carrier_id
JOIN lh_reference.dbo.ref_regions   AS r ON r.region_id  = o.region_id
GROUP BY c.carrier_name, r.remoteness
ORDER BY c.carrier_name, r.remoteness;

-- ---------------------------------------------------------------------------------------------
-- 3. CTAS: materialise a warehouse table from the cross-database query.
--    CTAS needs the destination not to exist, so drop it first (idempotent demo).
IF OBJECT_ID('dbo.late_rate_by_carrier_region') IS NOT NULL
    DROP TABLE dbo.late_rate_by_carrier_region;

CREATE TABLE dbo.late_rate_by_carrier_region
AS
SELECT c.carrier_id, c.carrier_name, r.region_id, r.region_name, r.remoteness,
       COUNT(*)                                    AS orders,
       SUM(CAST(o.is_late AS INT))                 AS late_orders,
       CAST(AVG(CAST(o.is_late AS FLOAT)) AS DECIMAL(5,3)) AS late_rate,
       CAST(SUM(o.order_value) AS DECIMAL(12,2))   AS revenue
FROM lh_reference.dbo.sample_orders AS o
JOIN lh_reference.dbo.ref_carriers  AS c ON c.carrier_id = o.carrier_id
JOIN lh_reference.dbo.ref_regions   AS r ON r.region_id  = o.region_id
GROUP BY c.carrier_id, c.carrier_name, r.region_id, r.region_name, r.remoteness;

-- 4. Read it back - this is now a warehouse table (writable, T-SQL DML works here, unlike the read-only SQL analytics endpoint).
SELECT TOP 10 * FROM dbo.late_rate_by_carrier_region ORDER BY late_rate DESC;

-- Talking point: the lakehouse SQL analytics endpoint is read-only; the warehouse is where you CREATE/INSERT/UPDATE with T-SQL.
-- Both are Delta/Parquet in OneLake underneath, which is why the cross-database join needs no copy.
