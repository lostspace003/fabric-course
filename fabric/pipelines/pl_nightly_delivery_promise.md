# pl_nightly_delivery_promise - re-score all open orders every morning (Lab 6 step 2)

**Pattern:** Copy data (SQL database → lakehouse table, overwrite) → Notebook `nb_02_features` (`mode=open_orders`) → Notebook `nb_04_batch_score`.
Each arrow is an **On success** dependency, so a failed copy never scores stale features.

```
[Copy open_orders] --success--> [nb_02_features mode=open_orders] --success--> [nb_04_batch_score]
```

## 1. Create

Workspace `ws-brightcart-dp` → **+ New item** → **Pipeline** → `pl_nightly_delivery_promise`.

## 2. Parameters (optional but handy)

| Name | Type | Default |
|---|---|---|
| `modelVersion` | Int | `0` (0 = latest registered version; Lab 7 can pin `2`) |

## 3. Activity 1 - Copy data `CopyOpenOrders`

| Tab | Setting | Value |
|---|---|---|
| Source | Connection | `sqldb_brightcart_ops` (**SQL database** in the workspace of Part 2, `ws-fabric-tour`). Create the connection with your organizational account. ⟲ verify the picker shows items from the other workspace; if not, use **More → OneLake catalog**. |
| Source | Use query | **Table** → `dbo.open_orders` (or **Query**: `SELECT * FROM dbo.open_orders WHERE status = 'in_transit'`) |
| Destination | Connection | `lh_brightcart` |
| Destination | Root folder | **Tables** |
| Destination | Table | `bronze_open_orders` (schema `dbo` if the lakehouse has schemas enabled) |
| Destination | Table action | **Overwrite** |
| Destination | Apply V-Order | leave default |
| Mapping | | leave empty (auto: same column names; `order_ts` DATETIME2 → timestamp, `promised_date` DATE → date) |

## 4. Activity 2 - Notebook `BuildOpenOrderFeatures`

| Setting | Value |
|---|---|
| Workspace | `ws-brightcart-dp` |
| Notebook | `nb_02_features` |
| Base parameters | `mode` (String) = `open_orders` |

Select **Auto-populate base parameters** if offered: it reads the notebook's tagged parameters cell and lists `mode` and `holdout_from`
(only override `mode`). ⟲ verify the toggle name. Connection: your user; or a Workspace Identity (Contributor) for unattended runs.

Link: drag from the Copy activity's green ✓ (On success) to this activity.

## 5. Activity 3 - Notebook `ScoreOpenOrders`

| Setting | Value |
|---|---|
| Notebook | `nb_04_batch_score` |
| Base parameters | `model_version` (Int) = `@pipeline().parameters.modelVersion` |

Leave `model_name`, `input_table`, `output_table` at their notebook defaults. Link: On success from Activity 2.

Optional **Session tag** (both notebook activities, same string, e.g. `nightly`) reuses one Spark session if the workspace's
*High concurrency for pipelines* setting is on - saves ~2 minutes of start-up. ⟲ verify setting location.

## 6. Run, then schedule

1. **Home → Save → Run**. Expected: three green activities; Output shows ~1,500 rows copied; the notebooks print their check cells.
2. **Home → Schedule**: On · Repeat **Daily** · Time **06:00** · Time zone: the learner's local zone · Start today · End: a month out. **Apply**. ⟲ verify the dialog fields.
3. ✅ `gold_open_orders_scored` exists with `late_risk`, `risk_band`, `scored_at`; the Power BI card **At-Risk Revenue** shows a value (Direct Lake, no import refresh).

## 7. Optional - failure notification

Add an **Outlook** (or **Teams**) activity linked with **On failure** from each step. Needs a mailbox / Teams licence on the account - personal-email tenants
may not have one; skip in that case. ⟲ verify the activity appears in the Activities list for your tenant.
Subject suggestion: `@{concat('pl_nightly_delivery_promise failed: ', activity('CopyOpenOrders').error.message)}` (adjust per activity).

## 8. Expressions used

| Where | Expression |
|---|---|
| Notebook base parameter `model_version` | `@pipeline().parameters.modelVersion` |
| Optional query filter by as-of day | `SELECT * FROM dbo.open_orders WHERE order_ts >= DATEADD(day, -3, '@{formatDateTime(utcNow(), 'yyyy-MM-dd')}')` |

## 9. If this fails

| Symptom | Fix |
|---|---|
| Copy: "table not found" | run `data/ops/sqldb_ops_setup.sql` in the SQL database (demo 2.5) |
| nb_02: `bronze_open_orders` not found | Copy wrote into a different schema/lakehouse; check the destination tab |
| nb_04: model not found | the notebook resolves the newest version of `mdl_delivery_promise`; Lab 3 must have run |
| nb_04: assertion "late_risk looks like a 0/1 label" | a classifier was registered; re-run `nb_03_train` (native Booster) |
| Cleanup (Lab 7) | **Schedule → Off**, so the trial capacity is not used every morning |
