# Cost guardrails

The owner's rule for this course: use the capacity smartly. Parts 1–3 run on the **Fabric trial**; the **F2** in the Azure
subscription exists for Lab 4's fallback and the optional 3.8 / 3.9 only, and is **paused** whenever a session ends.

## Every recording day
| When | Do | Why |
|---|---|---|
| Start | Resume F2 only if today needs it (3.8, 3.9, or a Lab 4 session the trial could not run) | F SKUs bill per second, 1-minute minimum |
| During Lab 4 / 5 / 7 | Leave **auto sleep on** for the endpoint (idle → scales to zero after 5 min) | an active node costs 5 CU-s per second (kit 02 §12) |
| End | `mdl_delivery_promise › Manage endpoints` → **Deactivate** every version | an active endpoint keeps drawing capacity |
| End | `pl_nightly_delivery_promise` → schedule **Off** | avoids a 06:00 run that burns CUs and re-scores stale data |
| End | Stop the Streamlit app (Ctrl+C) | it polls the endpoint |
| End | Azure portal › the F2 capacity → **Pause** | the meter stops |

## Facts the course states on screen (kit 03 §5, §8; prices ⟲ verify for the region)
- Trial: 60 days, 4 or 64 CUs, 1 TB OneLake, Power BI individual trial. Not production.
- F2 ≈ US$0.36 / hour pay-as-you-go (2025 list price) ≈ $0.72 for a 2-hour optional session.
- Trial ends → workspaces revert to Pro, non-Power BI items stop; content kept 7 days to move to F/P capacity.

## Say it out loud (teaching rule)
Whenever something starts using capacity (endpoint activation, a schedule, a running Spark session), the narration says so.
