# sm_delivery_promise + rpt_delivery_promise_ops - build spec (Lab 6 steps 3-4; pages 2-3 are homework)

## 1. Create the semantic model (Direct Lake)

Default semantic models are **no longer created automatically** since 5 September 2025 (existing ones were decoupled by 30 November 2025),
so you create one on purpose:

1. Open `lh_brightcart` → **New semantic model** (ribbon). ⟲ verify the button label; it also appears on the SQL analytics endpoint page.
2. Name: `sm_delivery_promise`. Workspace: `ws-brightcart-dp`.
3. Tick exactly these tables, then **Confirm**:
   `gold_fact_orders`, `gold_dim_date`, `gold_dim_carrier`, `gold_dim_region`, `gold_dim_warehouse`, `gold_open_orders_scored`, `gold_holdout_scored`.
4. The model opens in the web editor (**Open data model** later). If it does not, check the browser's pop-up blocker.
5. Storage mode is **Direct Lake**: the model reads the Delta files in OneLake directly. There is no import refresh: when `pl_nightly_delivery_promise`
   rewrites `gold_open_orders_scored`, the report shows the new rows on the next visual query (re-framing is automatic; a manual **Refresh** on the
   model only re-frames). ⟲ verify at recording that the At-risk cards change after a pipeline run with no refresh.
   - From the SQL analytics endpoint page you may be asked to choose **Direct Lake on OneLake** vs **Direct Lake on SQL**; either works here.

## 2. Relationships (model view → drag, or Manage relationships)

All **many-to-one**, **single** cross-filter direction, fact → dimension.

| From (many) | To (one) | Active | Notes |
|---|---|---|---|
| `gold_fact_orders[carrier_id]` | `gold_dim_carrier[carrier_id]` | yes | |
| `gold_fact_orders[region_id]` | `gold_dim_region[region_id]` | yes | |
| `gold_fact_orders[warehouse_id]` | `gold_dim_warehouse[warehouse_id]` | yes | |
| `gold_fact_orders[date_key]` | `gold_dim_date[date_key]` | yes | integer yyyymmdd on both sides |
| `gold_open_orders_scored[carrier_id]` | `gold_dim_carrier[carrier_id]` | yes | needed for "at-risk revenue by carrier" |
| `gold_open_orders_scored[region_id]` | `gold_dim_region[region_id]` | yes | |
| `gold_open_orders_scored[warehouse_id]` | `gold_dim_warehouse[warehouse_id]` | yes | |

`gold_holdout_scored` stays **unrelated** (analysed by its own `risk_decile` column). Mark `gold_dim_date` as a date table on `[date]`.
Hide key columns on the fact tables; set `gold_dim_date[month_name]` to sort by `[month]`.

## 3. Measures

Paste everything in `measures.dax` (New measure, one at a time). Home tables: `gold_fact_orders` for delivery measures,
`gold_open_orders_scored` for risk measures, `gold_holdout_scored` for calibration. Formats: rates as percentage (1 dp), revenue as currency.

## 4. Report `rpt_delivery_promise_ops` (New report from the semantic model)

### Page 1 - Today's risk (built live in Lab 6)

| Visual | Fields | Notes |
|---|---|---|
| Card | `[Open Orders]` | |
| Card | `[At-Risk Orders]` | subtitle "late_risk ≥ 0.6" |
| Card | `[At-Risk Revenue]` | the ✅ checkpoint card |
| Card | `[Last Scored At]` | proves the nightly run |
| Clustered bar chart | Y `gold_dim_carrier[carrier_name]`, X `[At-Risk Revenue]` | sort descending |
| Table (top 20) | `gold_open_orders_scored[order_id]`, `[late_risk]`, `[risk_band]`, `[order_value]`, `[ship_method]`, `[promised_date]`, `gold_dim_carrier[carrier_name]`, `gold_dim_region[region_name]` | Filters on this visual: Top N = 20 by `late_risk`; conditional colour on `late_risk` (0.35 amber, 0.6 red) |
| Slicer | `gold_open_orders_scored[risk_band]` | |

### Page 2 - Delivery performance (homework)

| Visual | Fields |
|---|---|
| Line chart | X `gold_dim_date[year_month]`, Y `[Late Rate]` |
| Clustered column | X `gold_dim_carrier[carrier_name]`, Y `[Late Rate]`, legend `gold_dim_region[remoteness_label]` |
| Matrix | rows `gold_dim_region[region_name]`, columns `gold_dim_carrier[carrier_name]`, values `[Late Rate]`, `[Orders]` |
| Cards | `[Late Rate Peak]`, `[Late Rate Off-peak]`, `[Peak Late Rate Ratio]` (target ≥ 1.5) |
| Slicers | `gold_dim_date[year]`, `gold_fact_orders[ship_method]`, `gold_fact_orders[split]` |

### Page 3 - Model health (homework)

| Visual | Fields | Notes |
|---|---|---|
| Line and clustered column chart | X `gold_holdout_scored[risk_decile]`, columns `[Holdout Orders]`, lines `[Holdout Avg Predicted Risk]` and `[Holdout Late Rate]` | the calibration chart: the two lines should sit on top of each other |
| Card | `[Expected Calibration Error]` | lower is better |
| Card | `[Top Decile Lift]` | |
| Card | `[Holdout AUC (text)]` | type the AUC from `exp_delivery_promise` into the measure (see measures.dax) |
| Table | `risk_decile`, `[Holdout Orders]`, `[Holdout Avg Predicted Risk]`, `[Holdout Late Rate]`, `[Calibration Gap]` | |

## 5. Checkpoint (Lab 6 ✅)

- The **At-Risk Revenue** card shows a value.
- Run `pl_nightly_delivery_promise` again, then interact with the report: the cards and `[Last Scored At]` change with **no import refresh** (Direct Lake).

## 6. Gotchas

- If a table is missing from the picker, refresh the SQL analytics endpoint page (metadata sync) and try again.
- Direct Lake falls back to DirectQuery (through the SQL analytics endpoint) for unsupported features or when limits are hit; the report still works.
- `gold_dim_date[date]` is a DATE column; `date_key` is an integer. Relate on `date_key`, display `date`.
