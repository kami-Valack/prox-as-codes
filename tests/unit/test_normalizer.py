from datetime import datetime, timezone
from types import SimpleNamespace

from proxy_as_code.capture.normalizer import flow_to_record


class Headers:
    def items(self, multi: bool = False):
        return []


def test_flow_to_record_uses_mitmproxy_timestamp_fields():
    flow = SimpleNamespace(
        request=SimpleNamespace(
            method="POST",
            pretty_url="https://tracking.bolt.eu/g/collect",
            host="tracking.bolt.eu",
            headers=Headers(),
            timestamp_start=10.0,
            timestamp_end=10.2,
        ),
        response=SimpleNamespace(
            status_code=200,
            headers=Headers(),
            timestamp_start=10.3,
            timestamp_end=10.5,
        ),
    )
    captured_at = datetime(2026, 10, 27, tzinfo=timezone.utc)

    record = flow_to_record(
        flow,
        request_body_ref=None,
        response_body_ref=None,
        captured_at=captured_at,
    )

    assert record.host == "tracking.bolt.eu"
    assert record.path == "/g/collect"
    assert record.response_status == 200
    assert record.duration_ms == 500.0
    assert record.captured_at == captured_at
