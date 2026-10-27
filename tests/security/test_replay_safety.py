from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from proxy_as_code.capture.models import HeaderPair, OriginalRecord
from proxy_as_code.config import AppConfig, ReplaySettings
from proxy_as_code.replay.executor import ReplayExecutor
from proxy_as_code.replay.safety import ReplaySafetyError, ReplaySafetyGate
from proxy_as_code.filtering.rules import ReplayPolicy
from proxy_as_code.storage.repository import TrafficRepository


@pytest.fixture
def repo(tmp_path: Path) -> TrafficRepository:
    return TrafficRepository(tmp_path / "t.db", tmp_path / "blobs")


def test_replay_requires_approval():
    policy = ReplayPolicy(ReplaySettings(require_approval=True, approval_token="secret"))
    gate = ReplaySafetyGate(policy)
    with pytest.raises(ReplaySafetyError):
        gate.check_approval(approved=False, approval_header=None)
    assert gate.check_approval(approved=False, approval_header="secret") == "token"


def test_replay_blocks_disallowed_host(repo: TrafficRepository):
    config = AppConfig(
        replay=ReplaySettings(
            require_approval=False,
            allowed_domains=["allowed.test"],
        )
    )
    record = OriginalRecord(
        id=uuid4(),
        method="GET",
        url="https://blocked.test/",
        host="blocked.test",
        path="/",
        query="",
        scheme="https",
        request_headers=[HeaderPair(name="Host", value="blocked.test")],
        captured_at=datetime.now(timezone.utc),
    )
    repo.insert_transaction(record)
    executor = ReplayExecutor(config, repo)
    with pytest.raises(ReplaySafetyError):
        executor.replay(record.id, approved=True)
