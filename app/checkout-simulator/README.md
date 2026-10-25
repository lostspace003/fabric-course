# Brightcart checkout simulator

The consumer of the `mdl_delivery_promise` model (kit/02 §7). It places one order or simulates N
checkouts, asks the model for `late_risk`, applies the decision policy and (optionally) sends one
event per checkout to the eventstream `es_checkout_events`.

## Run in mock mode (no Fabric needed)

```bash
pip install -r requirements.txt
copy .env.example .env          # APP_MODE=mock is already set
streamlit run app.py
```

Mock mode uses a local formula with the same coefficients as the data generator
(`data/generator/config.yaml`), so decisions look like the real model's.

## Run in live mode (Lab 4)

1. Activate the endpoint: open `mdl_delivery_promise` > version 1 > **Activate version endpoint**, then
   under **Manage endpoints** set the default version to 1.
2. Identity (kit/03 §7): create the Entra app registration `sp-brightcart-checkout-app` with a client secret,
   turn on the tenant setting **Service principals can call Fabric public APIs**, and add the service
   principal as **Contributor** on `ws-brightcart-dp` (scoring needs write permission on the model).
3. Fill `.env`: `APP_MODE=live`, `FABRIC_TENANT_ID`, `FABRIC_CLIENT_ID`, `FABRIC_CLIENT_SECRET`,
   `FABRIC_WORKSPACE_ID`, `FABRIC_MODEL_ID`. Leave `FABRIC_MODEL_VERSION` blank for the default version, or
   set it (for example `1`) to call `/endpoint/versions/1/score` (copy the exact URL from **Endpoint details**).
4. `streamlit run app.py`, place one order, then **Simulate 50 checkouts**.

Developer shortcut: `FABRIC_AUTH=cli` uses your own `az login --allow-no-subscriptions` token instead of the
service principal.

For Lab 5, paste the eventstream custom endpoint's **Connection string-primary key** (Event Hub protocol)
into `EVENTSTREAM_CONNECTION_STRING`. It already contains `EntityPath=...`; `EVENTSTREAM_ENTITY_NAME` is only
needed if yours does not.

## The score call

```
POST https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/mlModels/{MODEL_ID}/endpoint/score
{"formatType": "dataframe", "orientation": "values", "inputs": [[...16 values in contract order...]]}
-> {"formatType": "dataframe", "orientation": "values", "predictions": [[late_risk]]}
```

Token scope: `https://api.fabric.microsoft.com/.default`.

## If this fails

| Status | Meaning | Fix |
|---|---|---|
| 401 | Token rejected | Scope must be `https://api.fabric.microsoft.com/.default`; check tenant/client ID and secret |
| 403 | Identity not allowed | Tenant setting "Service principals can call Fabric public APIs" + Contributor role on the workspace |
| 404 | Not found | Workspace ID, model ID or version is wrong, or the endpoint is not active |
| 202 | Endpoint waking up (auto sleep after 5 min idle) | The app polls `Location` every `Retry-After` seconds, shows "Waking up the model..." and gives up after 90 s |
| Status "Failed" in Fabric | Schema or flavor problem | See kit/02 §5 (column-based signature, LightGBM native Booster) |

## Files

- `app.py` - Streamlit UI (sidebar status, place an order, simulate N)
- `fabric_client.py` - token, score call, 202 polling, friendly errors
- `mock.py` - local logit approximation + random orders from the generator's distributions
- `policy.py` - contract columns, decision policy, small lookups
- `events.py` - azure-eventhub producer; no-op when the connection string is unset
- `tests/` - `pytest tests -q`

## Tests

```bash
python -m pytest tests -q
```

Covers: request column order == contract order, decision boundaries 0.35/0.6, 202 polling with a fake
session, event schema validation, mock mode with no environment.
