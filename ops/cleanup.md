# Cleanup (taught in Lab 7, run after every recording day)

1. **Endpoints.** `ws-brightcart-dp › mdl_delivery_promise › Manage endpoints` ⟲ verify at recording → deactivate every version
   (v1 and v2). The list must show nothing active.
2. **Schedules.** `pl_nightly_delivery_promise › Schedule` → turn off. (Optional 3.8: nothing scheduled.)
3. **App.** Stop `streamlit run app.py`; clear `.env` values you no longer need. Secrets never go into the repo.
4. **Eventstream.** Leave `es_checkout_events` in place (no cost while no events arrive). Delete the custom-endpoint SAS key
   if the course secret was shown anywhere (it never should be).
5. **Paid capacity.** Azure portal › Microsoft Fabric › the F2 capacity → **Pause**. Resume only for the next paid session.
6. **Trial end.** After 60 days the workspaces fall back to Pro and the Fabric items become inactive; OneLake keeps the content
   for 7 days. To keep it, assign `ws-fabric-tour` and `ws-brightcart-dp` to a paid F capacity in that window.
7. **Delete everything (after the course).** Delete both workspaces (this removes every item, including the registered
   model, eventhouse data and the SQL database), the Entra app registration `sp-brightcart-checkout-app`, and the F2
   capacity if it is no longer needed.

Rehearsal copies in the owner's tenant use the prefix `rehearsal-` and are deleted the same way before recording.
