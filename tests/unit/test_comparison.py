from proxy_as_code.capture.models import HeaderPair
from proxy_as_code.replay.comparison import compare_responses


def test_compare_detects_status_and_body_diff():
    diff = compare_responses(
        200,
        [HeaderPair(name="Content-Type", value="application/json")],
        b'{"ok":true}',
        500,
        [HeaderPair(name="Content-Type", value="application/json")],
        b'{"ok":false}',
    )
    assert diff["status"]["equal"] is False
    assert diff["body"]["equal"] is False
