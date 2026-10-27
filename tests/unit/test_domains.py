from proxy_as_code.filtering.domains import should_capture_host, is_replay_allowed_host


def test_exact_host_no_substring_false_positive():
    assert should_capture_host("example.test", ["example.test"], []) is True
    assert should_capture_host("notexample.test", ["example.test"], []) is False


def test_exclude_over_include():
    assert (
        should_capture_host(
            "analytics.example.test",
            ["*.example.test", "example.test"],
            ["analytics.example.test"],
        )
        is False
    )


def test_wildcard_suffix():
    assert should_capture_host("api.example.test", ["*.api.example.test"], []) is True
    assert should_capture_host("v1.api.example.test", ["*.api.example.test"], []) is True
    assert should_capture_host("other.example.test", ["*.api.example.test"], []) is False


def test_replay_allowed_independent():
    assert is_replay_allowed_host("example.test", ["example.test"]) is True
    assert is_replay_allowed_host("api.example.test", ["example.test"]) is False
