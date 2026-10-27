from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from proxy_as_code.capture.models import ArtifactKind, GeneratedArtifact, HeaderPair, OriginalRecord
from proxy_as_code.storage.repository import TrafficRepository


def test_insert_search_and_artifacts(tmp_path: Path):
    repo = TrafficRepository(tmp_path / "t.db", tmp_path / "blobs")
    tid = uuid4()
    ref = repo.store_body(b"hello")
    record = OriginalRecord(
        id=tid,
        method="GET",
        url="https://example.test/path",
        host="example.test",
        path="/path",
        query="",
        scheme="https",
        request_headers=[HeaderPair(name="Accept", value="*/*")],
        request_body_ref=ref,
        response_status=200,
        response_headers=[],
        response_body_ref=ref,
        captured_at=datetime.now(timezone.utc),
    )
    repo.insert_transaction(record)
    repo.insert_artifact(
        GeneratedArtifact(
            transaction_id=tid,
            kind=ArtifactKind.PYTHON,
            content="print('x')",
            compiler_version="0.1.0",
            created_at=datetime.now(timezone.utc),
        )
    )
    found = repo.search_transactions(host="example.test")
    assert len(found) == 1
    assert repo.get_transaction(tid) is not None
    arts = repo.get_artifacts(tid, ArtifactKind.PYTHON)
    assert len(arts) == 1
