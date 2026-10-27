from datetime import datetime, timezone
from uuid import uuid4

from proxy_as_code.capture.models import HeaderPair, OriginalRecord
from proxy_as_code.compiler.curl import compile_curl
from proxy_as_code.compiler.python import compile_python


def _sample_record(**kwargs) -> OriginalRecord:
    defaults = dict(
        id=uuid4(),
        method="POST",
        url="https://api.example.test/api/v1/profile?q=1&q=2",
        host="api.example.test",
        path="/api/v1/profile",
        query="q=1&q=2",
        scheme="https",
        request_headers=[
            HeaderPair(name="Authorization", value="Bearer SECRET"),
            HeaderPair(name="Content-Type", value="application/json"),
        ],
        captured_at=datetime.now(timezone.utc),
        response_status=200,
    )
    defaults.update(kwargs)
    return OriginalRecord(**defaults)


def test_compile_python_includes_method_and_token_placeholder():
    code = compile_python(_sample_record(), b'{"name":"Test"}')
    assert "def replay_" in code
    assert "client.request" in code
    assert "Bearer {token}" in code or "token" in code


def test_compile_curl_uses_data_raw():
    curl = compile_curl(_sample_record(), b'{"a":1}')
    assert "curl" in curl
    assert "--data-raw" in curl
