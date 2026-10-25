"""Brightcart checkout simulator (kit/02 §7). Run: streamlit run app.py

Mock mode (APP_MODE=mock) needs no Fabric. Live mode calls the ML model endpoint (Lab 4)
and, when EVENTSTREAM_CONNECTION_STRING is set, sends one event per checkout (Lab 5).
"""
import json
import os
import random
import time

from dotenv import load_dotenv

load_dotenv()  # reads .env next to this file (never commit a real .env)

from policy import (CONTRACT_COLUMNS, CARRIERS, WAREHOUSES, REGIONS, BACKLOG_LOOKUP, FORECAST_LOOKUP,
                    ALERT_RISK, ALERT_VALUE, decision_policy)
from mock import mock_score, random_orders, MOCK_MODEL_VERSION
from fabric_client import FabricClient, FabricError, build_request
from events import EventSender, build_event, new_order_id

APP_MODE = os.getenv("APP_MODE", "mock").lower()


def model_version_label() -> str:
    """The version we are calling. The score response itself has no version field, so in live mode
    this comes from FABRIC_MODEL_VERSION or is 'default' (set under Manage endpoints). ⟲ verify at recording"""
    if APP_MODE == "mock":
        return MOCK_MODEL_VERSION
    return os.getenv("FABRIC_MODEL_VERSION") or "default"


def score_rows(rows: list[list], client: FabricClient | None, on_wait=None) -> tuple[list[float], int]:
    """Score rows in the current mode. Returns (late_risks, latency_ms)."""
    t0 = time.perf_counter()
    if APP_MODE == "mock":
        risks = mock_score(rows)
    else:
        if on_wait:
            client.on_wait = on_wait
        risks = client.score(rows)
    return risks, int((time.perf_counter() - t0) * 1000)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Brightcart checkout", page_icon=":package:", layout="wide")
    st.title("Brightcart checkout simulator")

    client = None if APP_MODE == "mock" else FabricClient()
    sender = EventSender()

    # ---- Sidebar: mode, model version, endpoint status --------------------------------------
    with st.sidebar:
        st.header("Status")
        st.metric("Mode", APP_MODE)
        st.metric("Model version", model_version_label())
        if APP_MODE == "mock":
            st.write("Endpoint: local formula (no Fabric call)")
        else:
            status = st.session_state.get("last_status")
            st.write("Endpoint:", client.url)
            st.write("Last HTTP status:", status if status is not None else "not called yet")
        st.write("Eventstream:", "configured" if sender.configured else "not configured (events skipped)")
        st.caption("Decision policy: < 0.35 keep | 0.35-0.6 extend | >= 0.6 offer express (standard) / extend (express)")

    # ---- Place an order ----------------------------------------------------------------------
    st.subheader("Place an order")
    with st.form("order"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            carrier_id = st.selectbox("carrier_id", list(CARRIERS), format_func=lambda k: f"{k} {CARRIERS[k]}")
            express = st.selectbox("ship_method_express", [0, 1], format_func=lambda v: "1 express" if v else "0 standard")
            warehouse_id = st.selectbox("warehouse_id", list(WAREHOUSES), format_func=lambda k: f"{k} {WAREHOUSES[k]}")
            region_id = st.selectbox("region_id", list(REGIONS), format_func=lambda k: f"{k} {REGIONS[k][0]}")
        with c2:
            remoteness = st.number_input("remoteness (0 urban .. 3 remote)", 0, 3, REGIONS[region_id][1])
            distance_km = st.number_input("distance_km", 1.0, 2000.0, float(REGIONS[region_id][3]))
            order_hour = st.number_input("order_hour (UTC)", 0, 23, 14)
            order_dow = st.number_input("order_dow (Mon = 0)", 0, 6, 2)
        with c3:
            is_weekend = st.selectbox("is_weekend", [0, 1], index=1 if order_dow >= 5 else 0)
            is_peak = st.selectbox("is_peak", [0, 1])
            items_count = st.number_input("items_count", 1, 12, 2)
            total_weight_kg = st.number_input("total_weight_kg", 0.1, 100.0, 2.4)
        with c4:
            order_value = st.number_input("order_value", 1.0, 100000.0, 89.0)
            promised_days = st.number_input("promised_days", 1, 7, 2 if express else 4)
            # Prefilled from the small lookup, but editable.
            backlog_index = st.number_input("backlog_index (yesterday)", 0.3, 1.6, BACKLOG_LOOKUP[warehouse_id])
            forecast_severity = st.number_input("forecast_severity (0..3)", 0, 3, FORECAST_LOOKUP[region_id])
        placed = st.form_submit_button("Score this order")

    if placed:
        order = {
            "carrier_id": int(carrier_id), "ship_method_express": int(express), "warehouse_id": int(warehouse_id),
            "region_id": int(region_id), "remoteness": int(remoteness), "distance_km": float(distance_km),
            "order_hour": int(order_hour), "order_dow": int(order_dow), "is_weekend": int(is_weekend),
            "is_peak": int(is_peak), "items_count": int(items_count), "total_weight_kg": float(total_weight_kg),
            "order_value": float(order_value), "promised_days": int(promised_days),
            "backlog_index": float(backlog_index), "forecast_severity": int(forecast_severity),
        }
        row = [order[c] for c in CONTRACT_COLUMNS]       # contract order, always
        wait_box = st.empty()
        try:
            risks, latency_ms = score_rows([row], client, on_wait=lambda m: wait_box.info(m))
            wait_box.empty()
        except FabricError as exc:
            wait_box.empty()
            st.error(str(exc))
            risks = None
        if client is not None:
            st.session_state["last_status"] = client.last_status
        if risks:
            late_risk = risks[0]
            decision = decision_policy(late_risk, order["ship_method_express"])
            r1, r2, r3 = st.columns(3)
            r1.metric("late_risk", f"{late_risk:.2f}")
            r1.progress(min(1.0, max(0.0, late_risk)))
            r2.metric("decision", decision.replace("_", " "))
            r3.metric("latency", f"{latency_ms} ms")
            if late_risk >= ALERT_RISK and order["order_value"] >= ALERT_VALUE:
                st.warning("This order would trigger the Activator alert (late_risk >= 0.7 and order_value >= 200).")
            with st.expander("Request JSON"):
                st.code(json.dumps(build_request([row]), indent=2), language="json")
            if sender.configured:
                ev = build_event(order, late_risk, decision, model_version_label(), latency_ms)
                try:
                    sender.send([ev])
                    st.caption(f"Event {ev['order_id']} sent to the eventstream.")
                except Exception as exc:  # show, do not crash the app
                    st.error(f"Event not sent: {exc}")

    # ---- Simulate N checkouts ----------------------------------------------------------------
    st.subheader("Simulate checkouts")
    s1, s2, s3 = st.columns([1, 1, 2])
    n = s1.number_input("N", 1, 2000, 50)
    seed_text = s2.text_input("seed (blank = random)", "")
    if s3.button(f"Simulate {int(n)} checkouts"):
        seed = int(seed_text) if seed_text.strip().isdigit() else None
        orders = random_orders(int(n), seed)
        rows = [[o[c] for c in CONTRACT_COLUMNS] for o in orders]
        wait_box = st.empty()
        try:
            risks, latency_ms = score_rows(rows, client, on_wait=lambda m: wait_box.info(m))
            wait_box.empty()
        except FabricError as exc:
            wait_box.empty()
            st.error(str(exc))
            risks = None
        if client is not None:
            st.session_state["last_status"] = client.last_status
        if risks:
            rng = random.Random(seed)
            per_call = max(1, latency_ms // len(rows))
            events, table = [], []
            for o, risk in zip(orders, risks):
                decision = decision_policy(risk, o["ship_method_express"])
                ev = build_event(o, risk, decision, model_version_label(), per_call, order_id=new_order_id(rng))
                events.append(ev)
                table.append({"order_id": ev["order_id"], "region": REGIONS[o["region_id"]][0],
                              "carrier": CARRIERS[o["carrier_id"]], "ship_method": ev["ship_method"],
                              "order_value": o["order_value"], "late_risk": risk, "decision": decision})
            st.dataframe(table, use_container_width=True)
            counts = {}
            for t in table:
                counts[t["decision"]] = counts.get(t["decision"], 0) + 1
            st.write(f"{len(table)} checkouts scored in {latency_ms} ms. Decisions: {counts}")
            if sender.configured:
                try:
                    sent = sender.send(events)
                    st.success(f"{sent} events sent to the eventstream.")
                except Exception as exc:
                    st.error(f"Events not sent: {exc}")
            else:
                st.caption("Set EVENTSTREAM_CONNECTION_STRING in .env to send these as events (Lab 5).")


if __name__ == "__main__":
    main()
