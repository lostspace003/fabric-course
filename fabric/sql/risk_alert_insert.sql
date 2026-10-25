-- pl_log_alert: write one alert row into sqldb_brightcart_ops.dbo.risk_alerts (table created by data/ops/sqldb_ops_setup.sql).
-- Called by the Activator rule act_delivery_risk_alerts (Fabric item action) with parameters order_id, late_risk, order_value.
--
-- ============================================================================================
-- BLOCK 1 (primary) - Script activity, Fabric SQL database connection, type NonQuery.
-- Learn lists Fabric SQL database as a supported Script-activity store. ⟲ verify at recording that the connection
-- picker offers the SQL database item and that the run succeeds (kit open check 13).
--
-- Script parameters (Settings > Script parameters, "Named parameters"):
--   Name         Type     Value (dynamic content)
--   order_id     Int32    @pipeline().parameters.order_id
--   late_risk    Double   @pipeline().parameters.late_risk
--   order_value  Double   @pipeline().parameters.order_value
-- Named parameters are referenced as @<name> in the script text:
-- ============================================================================================
INSERT INTO dbo.risk_alerts (order_id, late_risk, order_value)
VALUES (@order_id, @late_risk, @order_value);
-- created_at fills itself (DEFAULT SYSUTCDATETIME()); alert_id is IDENTITY.


-- ============================================================================================
-- BLOCK 2 (fallback) - Stored procedure activity, if the Script activity will not take the SQL database connection.
-- Step A: run this once in the SQL database query editor to create the procedure.
-- ============================================================================================
CREATE OR ALTER PROCEDURE dbo.usp_log_risk_alert
    @order_id    INT,
    @late_risk   FLOAT,
    @order_value FLOAT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.risk_alerts (order_id, late_risk, order_value)
    VALUES (@order_id, @late_risk, @order_value);
END;
GO
-- Step B: in pl_log_alert replace the Script activity with a Stored procedure activity:
--   Connection: sqldb_brightcart_ops  ->  Stored procedure name: dbo.usp_log_risk_alert  ->  Import parameters, then set
--   order_id    = @pipeline().parameters.order_id
--   late_risk   = @pipeline().parameters.late_risk
--   order_value = @pipeline().parameters.order_value


-- ============================================================================================
-- Check (Lab 5 checkpoint): the newest alert rows.
-- ============================================================================================
SELECT TOP 20 alert_id, order_id, late_risk, order_value, created_at
FROM dbo.risk_alerts
ORDER BY created_at DESC;
