# pl_log_alert - write an alert row into `sqldb_brightcart_ops.dbo.risk_alerts` (Lab 5, Activator fallback)

Used when the Activator action **Fabric item → Pipeline** is chosen instead of email/Teams (works on personal-email tenants).
Activator passes three values; the pipeline inserts one row. SQL text lives in `fabric/sql/risk_alert_insert.sql`.

## 1. Create

Workspace `ws-brightcart-dp` → **+ New item** → **Pipeline** → `pl_log_alert`.

## 2. Parameters (canvas background → Parameters → + New)

| Name | Type | Default |
|---|---|---|
| `order_id` | String | `0` |
| `late_risk` | Float | `0` |
| `order_value` | Float | `0` |

`order_id` is String because Activator maps event fields as text; the SQL casts it. If the Activator parameter dialog offers typed values, Int also works.

## 3. Activity - Script `InsertRiskAlert` (primary path)

Learn lists **Fabric SQL database** among the Script activity's supported stores. ⟲ verify at recording (kit open check 13) that the connection picker
accepts `sqldb_brightcart_ops` and the run succeeds.

| Tab | Setting | Value |
|---|---|---|
| Settings | Connection | `sqldb_brightcart_ops` (SQL database, organizational account) |
| Settings | Script type | **NonQuery** |
| Settings | Script | `INSERT INTO dbo.risk_alerts (order_id, late_risk, order_value) VALUES (CAST(@order_id AS INT), @late_risk, @order_value);` |
| Settings → Script parameters | `order_id` | Type String, Value `@pipeline().parameters.order_id`, direction Input |
| | `late_risk` | Type Double, Value `@pipeline().parameters.late_risk` |
| | `order_value` | Type Double, Value `@pipeline().parameters.order_value` |

Named parameters are referenced as `@name` inside the script. Keep one statement per script block.

## 4. Fallback - Stored procedure activity

If the Script activity refuses the SQL database connection:

1. In the SQL database query editor run **BLOCK 2** of `fabric/sql/risk_alert_insert.sql` (creates `dbo.usp_log_risk_alert`).
2. Replace the Script activity with **Stored procedure**: Connection `sqldb_brightcart_ops` → Stored procedure name `dbo.usp_log_risk_alert` → **Import** parameters → values:
   `order_id` = `@int(pipeline().parameters.order_id)`, `late_risk` = `@pipeline().parameters.late_risk`, `order_value` = `@pipeline().parameters.order_value`.

## 5. Test by hand

**Run** → the parameter prompt appears → `order_id 999001`, `late_risk 0.82`, `order_value 345.5` → OK.
Then in the SQL database: `SELECT TOP 5 * FROM dbo.risk_alerts ORDER BY created_at DESC;` shows the row with `created_at` filled by default.

## 6. Hook it to the Activator

In `act_delivery_risk_alerts` (see `fabric/activator/act_delivery_risk_alerts.md`): Action **Fabric item** → pick `pl_log_alert` → **Add parameter** ×3:
`order_id` = `@order_id`, `late_risk` = `@late_risk`, `order_value` = `@order_value` (type `@` to pick event fields). ⟲ verify labels.

## 7. Schedule

None: Activator starts it per matching event. Expect one run per high-risk, high-value checkout (a 200-checkout simulation gives a handful).
