# act_delivery_risk_alerts - alert on high-risk, high-value checkouts (Lab 5 step 5, kit 02 §9)

Activator watches the eventstream and runs an action for every event that matches a rule. Here: `late_risk ≥ 0.7` **and** `order_value ≥ 200`.

## 1. Create the Activator from the eventstream

Two routes; pick one and ⟲ verify the labels at recording:

- **From the eventstream (preferred):** open `es_checkout_events` → **Edit** → **Add destination → Activator** → *Create new* Activator named
  `act_delivery_risk_alerts`, workspace `ws-brightcart-dp` → **Save → Publish**. Then open the Activator item.
- **From Real-Time hub:** Real-Time hub → **My data streams** (or *All data streams*) → row `es_checkout_events` → **Set alert** (⚡) → the rule
  dialog opens with the stream pre-selected; choose *Save location: new item* `act_delivery_risk_alerts`.

Events must already be flowing (run **Simulate 200 checkouts** in the app first) so Activator can show sample values.

## 2. Source and object

| Setting | Value |
|---|---|
| Stream | `es_checkout_events` (the default stream) |
| Object | Create object **Order**, ID column `order_id`; properties: `late_risk`, `order_value`, `carrier_id`, `region_id`, `decision`, `model_version` |

Why an object: rules are evaluated **per order_id**, so each checkout is one activation and the message can carry that order's fields.
(A rule straight on the stream, without an object, also works for this per-event case.)

## 3. Rule `High-risk high-value checkout`

| Setting | Value |
|---|---|
| Monitor | property `late_risk` |
| Condition | **On each event when** `late_risk` **Is greater than or equal to** `0.7` |
| Additional condition (+ Add condition / filter) | `order_value` **Is greater than or equal to** `200` |
| Check frequency | every event (stateless rule; sub-second latency) |

⟲ verify how the second condition is added (filter on the Monitor card vs "And" condition) - the UI has moved between releases.
The **Definition** tab's chart shows how many sample events would have fired; with the simulator's distribution expect a few per 200 checkouts.

## 4. Message

Template (type `@` to insert fields):

```
Order @order_id: @late_risk late risk, value @order_value.
```

Subject / headline: `Brightcart: high-risk order @order_id`. Context fields to include: `carrier_id`, `region_id`, `decision`, `model_version`.

## 5. Action - choose one

### Option A - Email or Teams message (needs a mailbox / Teams licence; usual on work accounts)

| Setting | Value |
|---|---|
| Action | **Email** → *To*: your work address, *Subject* as above, *Headline* / *Message* as above, *Context*: fields above |
| or | **Teams** → *Send to*: yourself (or a channel), same message |

### Option B - Fabric item → run `pl_log_alert` (works on personal-email tenants)

| Setting | Value |
|---|---|
| Action | **Fabric item** → **Pipeline** → select `pl_log_alert` (OneLake catalog picker) |
| Parameters | **+ Add parameter** three times: `order_id` = `@order_id` · `late_risk` = `@late_risk` · `order_value` = `@order_value` |

The pipeline inserts a row into `sqldb_brightcart_ops.dbo.risk_alerts` (see `fabric/pipelines/pl_log_alert.md`).
Supported Fabric-item actions per Learn: pipeline, notebook, Spark job definition, dataflow, user data function, copy job (no parameters), publish business event (preview); plus Power Automate custom actions.

## 6. Save, test, start

1. **Save** the rule. **Test action** sends one message / starts one pipeline run with a sample event. ⟲ verify button names.
2. **Start** (top ribbon). The rule stays running until you **Stop** it.
3. Run **Simulate 200 checkouts** again.
4. ✅ An email/Teams message arrives, or `SELECT TOP 5 * FROM dbo.risk_alerts ORDER BY created_at DESC` shows new rows. Latency: seconds for the rule, plus pipeline start-up (~30-60 s) for Option B.

## 7. Notes

- Activator fires and moves on; it does not wait for the pipeline to finish. Check pipeline runs in Monitoring hub.
- Rules evaluate per `order_id`; since each checkout is a new id, every matching event fires once (no "becomes" state needed).
- Cleanup (Lab 7): **Stop** the rule, or the trial capacity keeps evaluating events.
- Optional: turn on **OneLake availability** for `CheckoutScores` in `eh_brightcart` and shortcut it into `lh_brightcart` → live events become future training data. ⟲ verify
