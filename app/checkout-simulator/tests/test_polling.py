"""202 polling with a fake requests session: 202 then 200."""
import pytest

from fabric_client import FabricClient, FabricError, score_url


class FakeResponse:
    def __init__(self, status, headers=None, body=None, text=""):
        self.status_code = status
        self.headers = headers or {}
        self._body = body
        self.text = text

    def json(self):
        return self._body


class FakeSession:
    """Replays a list of responses in order; records the calls it saw."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url))
        return self.responses.pop(0)

    def get(self, url, headers=None, timeout=None):
        self.calls.append(("GET", url))
        return self.responses.pop(0)


class FakeCredential:
    def get_token(self, scope):
        assert scope == "https://api.fabric.microsoft.com/.default"
        return type("T", (), {"token": "fake"})()


def make_client(responses):
    sleeps = []
    client = FabricClient(workspace_id="ws", model_id="m", version=None, credential=FakeCredential(),
                          session=FakeSession(responses), sleep=sleeps.append)
    return client, sleeps


def test_200_direct():
    client, _ = make_client([FakeResponse(200, body={"predictions": [[0.81], [0.05]]})])
    assert client.score([[1] * 16, [2] * 16]) == [0.81, 0.05]
    assert client.session.calls[0] == ("POST", "https://api.fabric.microsoft.com/v1/workspaces/ws/mlModels/m/endpoint/score")


def test_202_then_200_with_predictions():
    responses = [
        FakeResponse(202, headers={"Location": "https://api.fabric.microsoft.com/v1/operations/op1", "Retry-After": "2"}),
        FakeResponse(200, body={"formatType": "dataframe", "orientation": "values", "predictions": [[0.42]]}),
    ]
    client, sleeps = make_client(responses)
    messages = []
    client.on_wait = messages.append
    assert client.score([[1] * 16]) == [0.42]
    assert sleeps == [2]
    assert client.session.calls[1] == ("GET", "https://api.fabric.microsoft.com/v1/operations/op1")
    assert messages and messages[0].startswith("Waking up the model")


def test_202_running_then_succeeded_then_result():
    op = "https://api.fabric.microsoft.com/v1/operations/op2"
    responses = [
        FakeResponse(202, headers={"Location": op, "Retry-After": "1"}),
        FakeResponse(200, headers={"Location": op, "Retry-After": "1"}, body={"status": "Running"}),
        FakeResponse(200, headers={"Location": op + "/result"}, body={"status": "Succeeded"}),
        FakeResponse(200, body={"predictions": [[0.7]]}),
    ]
    client, sleeps = make_client(responses)
    assert client.score([[1] * 16]) == [0.7]
    assert sleeps == [1, 1]
    assert client.session.calls[-1] == ("GET", op + "/result")


def test_202_gives_up_after_90s():
    responses = [FakeResponse(202, headers={"Location": "https://x/op", "Retry-After": "60"})]
    responses += [FakeResponse(202, headers={"Location": "https://x/op", "Retry-After": "60"})] * 5
    client, sleeps = make_client(responses)
    with pytest.raises(FabricError, match="90s"):
        client.score([[1] * 16])
    assert sum(sleeps) <= 90


@pytest.mark.parametrize("status,needle", [(401, "scope"), (403, "tenant setting"), (404, "model ID")])
def test_error_messages(status, needle):
    client, _ = make_client([FakeResponse(status, text="nope")])
    with pytest.raises(FabricError, match=needle):
        client.score([[1] * 16])


def test_version_pinned_url():
    assert score_url("ws", "m", "2").endswith("/mlModels/m/endpoint/versions/2/score")
    assert score_url("ws", "m").endswith("/mlModels/m/endpoint/score")
