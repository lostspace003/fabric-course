"""Call the Fabric ML model endpoint (kit/02 §7, Lab 4).

Score call (Learn: https://learn.microsoft.com/rest/api/fabric/mlmodel/endpoint/score-ml-model-endpoint):
    POST https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/mlModels/{MODEL_ID}/endpoint/score
    body {"formatType": "dataframe", "orientation": "values", "inputs": [[...16 values...], ...]}
    200  -> {"formatType": "dataframe", "orientation": "values", "predictions": [[late_risk], ...]}
    202  -> long-running operation: headers Location, x-ms-operation-id, Retry-After. Poll Location
            (Learn: https://learn.microsoft.com/rest/api/fabric/articles/long-running-operation).
Version-pinned path: .../endpoint/versions/{N}/score  (Learn says the UI "Endpoint details" URL
ends with /versions/1/score; copy the exact URL from the UI.  ⟲ verify at recording)
"""
import os
import time

import requests

FABRIC_API = "https://api.fabric.microsoft.com/v1"
SCOPE = "https://api.fabric.microsoft.com/.default"
MAX_WAIT_SECONDS = 90          # cap for the whole 202 wait
REQUEST_TIMEOUT = 30           # seconds for one HTTP call


class FabricError(Exception):
    """A scoring problem with a message the learner can act on (the Lab 4 'If this fails' table)."""


def _friendly(status: int, body: str) -> str:
    if status == 401:
        return ("401 Unauthorized: the token was rejected. Check the scope is "
                "https://api.fabric.microsoft.com/.default and that tenant/client ID and secret are right.")
    if status == 403:
        return ("403 Forbidden: the identity cannot score. Check the tenant setting 'Service principals "
                "can call Fabric public APIs' and that the service principal is Contributor on the workspace.")
    if status == 404:
        return "404 Not Found: the workspace ID, model ID or version is wrong (or the endpoint is not active)."
    if status == 429:
        return "429 Too Many Requests: slow down and retry after the Retry-After seconds."
    return f"HTTP {status}: {body[:300]}"


def build_credential():
    """Service principal by default; Azure CLI user token when FABRIC_AUTH=cli (developer shortcut)."""
    if os.getenv("FABRIC_AUTH", "sp").lower() == "cli":
        from azure.identity import AzureCliCredential  # az login --allow-no-subscriptions first
        return AzureCliCredential()
    from azure.identity import ClientSecretCredential
    missing = [k for k in ("FABRIC_TENANT_ID", "FABRIC_CLIENT_ID", "FABRIC_CLIENT_SECRET") if not os.getenv(k)]
    if missing:
        raise FabricError("Missing .env values: " + ", ".join(missing))
    return ClientSecretCredential(
        tenant_id=os.environ["FABRIC_TENANT_ID"],
        client_id=os.environ["FABRIC_CLIENT_ID"],
        client_secret=os.environ["FABRIC_CLIENT_SECRET"],
    )


def score_url(workspace_id: str, model_id: str, version: str | None = None) -> str:
    """Default-version URL, or the version-pinned URL when a version is given."""
    base = f"{FABRIC_API}/workspaces/{workspace_id}/mlModels/{model_id}/endpoint"
    if version:
        return f"{base}/versions/{version}/score"
    return f"{base}/score"


def build_request(rows: list[list]) -> dict:
    """The request body. Each inner list holds the 16 contract values in order."""
    return {"formatType": "dataframe", "orientation": "values", "inputs": rows}


class FabricClient:
    """Small wrapper: token, POST, 202 polling, friendly errors.

    `session` and `credential` can be swapped out in tests. `on_wait` is called with a message
    while we poll a 202, so the UI can show "Waking up the model...".
    """

    def __init__(self, workspace_id=None, model_id=None, version=None,
                 credential=None, session=None, sleep=time.sleep, on_wait=None):
        self.workspace_id = workspace_id or os.getenv("FABRIC_WORKSPACE_ID", "")
        self.model_id = model_id or os.getenv("FABRIC_MODEL_ID", "")
        self.version = version if version is not None else (os.getenv("FABRIC_MODEL_VERSION") or None)
        self._credential = credential
        self.session = session or requests.Session()
        self._sleep = sleep
        self.on_wait = on_wait or (lambda msg: None)
        self.last_status = None         # last HTTP status seen (for the sidebar)
        self.last_request = None        # last request body (for the collapsible JSON)

    @property
    def url(self) -> str:
        return score_url(self.workspace_id, self.model_id, self.version)

    def _headers(self) -> dict:
        if self._credential is None:
            self._credential = build_credential()
        try:
            token = self._credential.get_token(SCOPE).token
        except Exception as exc:  # azure-identity raises many types; show one clear message
            raise FabricError(f"Could not get a token: {exc}") from exc
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def score(self, rows: list[list]) -> list[float]:
        """Send the rows, return one late_risk per row."""
        if not self.workspace_id or not self.model_id:
            raise FabricError("FABRIC_WORKSPACE_ID and FABRIC_MODEL_ID must be set for live mode.")
        body = build_request(rows)
        self.last_request = body
        headers = self._headers()
        # An idle endpoint goes to sleep (auto sleep, 5 min); the first call after that can time out while it wakes up.
        # Dry run on a real endpoint (2026-10-25): first call timed out at 30 s, the next answered in ~20 ms per row.
        # So a timeout is retried until MAX_WAIT_SECONDS, telling the UI "Waking up the model...".
        started = time.monotonic()
        while True:
            try:
                resp = self.session.post(self.url, json=body, headers=headers, timeout=REQUEST_TIMEOUT)
                break
            except requests.Timeout as exc:
                if time.monotonic() - started + REQUEST_TIMEOUT > MAX_WAIT_SECONDS:
                    raise FabricError(f"Timed out after {int(time.monotonic() - started)}s calling the endpoint.") from exc
                self.on_wait("Waking up the model...")
            except requests.ConnectionError as exc:
                raise FabricError(f"Could not reach api.fabric.microsoft.com: {exc}") from exc
        self.last_status = resp.status_code

        if resp.status_code == 202:
            resp = self._poll(resp, headers)
        if resp.status_code != 200:
            raise FabricError(_friendly(resp.status_code, resp.text))
        return self._parse(resp.json(), len(rows))

    def _poll(self, resp, headers):
        """Standard Fabric LRO: wait Retry-After, GET Location, repeat until a result or 90 s."""
        started = time.monotonic()
        waited = 0                      # seconds we have asked to sleep so far
        location = resp.headers.get("Location")
        if not location:
            op_id = resp.headers.get("x-ms-operation-id")
            if not op_id:
                raise FabricError("202 without Location or x-ms-operation-id header.")
            location = f"{FABRIC_API}/operations/{op_id}"
        while True:
            wait = _retry_after(resp, default=5)
            elapsed = max(time.monotonic() - started, waited)
            if elapsed + wait > MAX_WAIT_SECONDS:
                raise FabricError(f"The endpoint did not answer within {MAX_WAIT_SECONDS}s. "
                                  "It may still be waking up: try again in a minute.")
            self.on_wait(f"Waking up the model... ({int(elapsed)}s)")
            self._sleep(wait)
            waited += wait
            try:
                resp = self.session.get(location, headers=headers, timeout=REQUEST_TIMEOUT)
            except requests.Timeout as exc:
                raise FabricError("Timed out while polling the operation.") from exc
            self.last_status = resp.status_code
            if resp.status_code == 202:
                continue                                   # still running
            if resp.status_code != 200:
                raise FabricError(_friendly(resp.status_code, resp.text))
            data = resp.json()
            if "predictions" in data:
                return resp                                # the result came back directly
            status = str(data.get("status", ""))
            if status in ("Running", "NotStarted"):
                # Running operations may move the Location header; follow it if given.
                location = resp.headers.get("Location", location)
                continue
            if status == "Succeeded":
                # Location now points at the result; if not, use the /result convention.
                result_url = resp.headers.get("Location") or (location.rstrip("/") + "/result")
                resp = self.session.get(result_url, headers=headers, timeout=REQUEST_TIMEOUT)
                self.last_status = resp.status_code
                return resp
            raise FabricError(f"Operation ended with status '{status}': {resp.text[:300]}")

    @staticmethod
    def _parse(data: dict, n: int) -> list[float]:
        preds = data.get("predictions")
        if preds is None:
            raise FabricError(f"No 'predictions' in the response: {str(data)[:300]}")
        out = []
        for p in preds:
            out.append(float(p[0]) if isinstance(p, (list, tuple)) else float(p))
        if len(out) != n:
            raise FabricError(f"Expected {n} predictions, got {len(out)}.")
        return out


def _retry_after(resp, default: int) -> int:
    try:
        return max(1, int(resp.headers.get("Retry-After", default)))
    except ValueError:
        return default
