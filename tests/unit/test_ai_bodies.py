from proxy_as_code.ai.bodies import encode_body_for_agent


def test_encode_body_text_and_truncation():
    raw = b'{"ok":true}'
    full = encode_body_for_agent(raw, max_bytes=1024)
    assert full["present"] is True
    assert full["text"] == '{"ok":true}'
    assert full["truncated"] is False

    big = b"x" * 100
    cut = encode_body_for_agent(big, max_bytes=10)
    assert cut["truncated"] is True
    assert cut["size_bytes"] == 100
