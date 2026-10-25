"""Dry-run helper = the app's 'Simulate N checkouts' without the UI: score on the live endpoint, send events to the eventstream.
   python ops/simulate_live.py [N] [seed]   (run from the repo root; reads app/checkout-simulator/.env)"""
import os, sys, time, random
sys.path.insert(0, "app/checkout-simulator")
from dotenv import load_dotenv; load_dotenv("app/checkout-simulator/.env")
import mock, policy, fabric_client as fc, events
n = int(sys.argv[1]) if len(sys.argv) > 1 else 200; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
c = fc.FabricClient(); s = events.EventSender(); print("sender configured:", s.configured)
orders = mock.random_orders(n, seed=seed); rng = random.Random(seed)
rows = [[o[k] for k in policy.CONTRACT_COLUMNS] for o in orders]
t = time.time(); risks = c.score(rows); lat = int((time.time() - t) * 1000 / len(rows))
print(f"scored {n}, HTTP {c.last_status}, {lat} ms/row; risk min {min(risks):.3f} max {max(risks):.3f}")
ver = os.getenv("FABRIC_MODEL_VERSION") or "2"
evs = [events.build_event(o, r, policy.decision_policy(r, int(o["ship_method_express"])), ver, lat, order_id=events.new_order_id(rng)) for o, r in zip(orders, risks)]
print("sent", s.send(evs))
