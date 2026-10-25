"""Send one JSON event per scored checkout to the eventstream's custom endpoint (Lab 5).

The custom endpoint source gives an Event Hub-compatible connection string
(Endpoint=sb://eventstream-xxx.servicebus.windows.net/;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=es_xxx)
so the normal azure-eventhub producer works. Learn:
https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-source-custom-app
https://learn.microsoft.com/azure/event-hubs/event-hubs-python-get-started-send

Event shape: kit/contracts/checkout_event.schema.json. Nothing is sent when the connection string is unset.
"""
import json
import os
import random
import socket
from datetime import datetime, timezone

APP_INSTANCE = os.getenv("APP_INSTANCE") or f"checkout-simulator@{socket.gethostname()}"


def new_order_id(rng: random.Random | None = None) -> str:
    """Simulated orders are 'S' + 7 digits, so they never clash with history."""
    rng = rng or random
    return "S" + str(rng.randint(0, 9_999_999)).zfill(7)


def build_event(order: dict, late_risk: float, decision: str, model_version: str,
                latency_ms: int, order_id: str | None = None, event_time: datetime | None = None) -> dict:
    """One event that validates against checkout_event.schema.json."""
    event_time = event_time or datetime.now(timezone.utc)
    return {
        "event_time": event_time.isoformat().replace("+00:00", "Z"),
        "order_id": order_id or new_order_id(),
        "region_id": int(order["region_id"]),
        "carrier_id": int(order["carrier_id"]),
        "ship_method": "express" if int(order["ship_method_express"]) == 1 else "standard",
        "order_value": float(order["order_value"]),
        "late_risk": float(late_risk),
        "decision": decision,
        "model_version": str(model_version),
        "latency_ms": int(latency_ms),
        "app_instance": APP_INSTANCE,
    }


class EventSender:
    """Batched sender. No-op (configured == False) when EVENTSTREAM_CONNECTION_STRING is empty."""

    def __init__(self, connection_string: str | None = None, entity_name: str | None = None):
        self.connection_string = connection_string if connection_string is not None \
            else os.getenv("EVENTSTREAM_CONNECTION_STRING", "")
        # The entity name is usually inside the connection string (EntityPath=...). Set it only if not.
        self.entity_name = entity_name if entity_name is not None else os.getenv("EVENTSTREAM_ENTITY_NAME", "")
        self.configured = bool(self.connection_string.strip())

    def send(self, events: list[dict]) -> int:
        """Send the events in as few batches as needed. Returns how many were sent."""
        if not self.configured or not events:
            return 0
        from azure.eventhub import EventHubProducerClient, EventData

        kwargs = {"conn_str": self.connection_string}
        if self.entity_name and "EntityPath=" not in self.connection_string:
            kwargs["eventhub_name"] = self.entity_name
        producer = EventHubProducerClient.from_connection_string(**kwargs)
        sent = 0
        with producer:
            batch = producer.create_batch()
            for ev in events:
                data = EventData(json.dumps(ev))
                try:
                    batch.add(data)
                except ValueError:          # batch is full: send it and start a new one
                    producer.send_batch(batch)
                    sent += len(batch)
                    batch = producer.create_batch()
                    batch.add(data)
            if len(batch) > 0:
                producer.send_batch(batch)
                sent += len(batch)
        return sent
