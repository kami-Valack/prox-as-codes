from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from proxy_as_code.app_context import AppContext
from proxy_as_code.capture.models import HeaderPair, OriginalRecord
from proxy_as_code.api.routes import create_api


def test_list_requests_returns_full_records_and_supports_pagination(
    tmp_path: Path,
):
    ctx = AppContext.create(
        config_path=tmp_path / "missing.yaml",
        base_dir=tmp_path,
    )
    now = datetime.now(timezone.utc)
    ids = [uuid4(), uuid4()]

    for index, transaction_id in enumerate(ids):
        body_ref = ctx.repository.store_body(f"request-{index}".encode())
        ctx.repository.insert_transaction(
            OriginalRecord(
                id=transaction_id,
                method="POST",
                url=f"https://example.test/{index}",
                host="example.test",
                path=f"/{index}",
                query="",
                scheme="https",
                request_headers=[HeaderPair(name="Content-Type", value="text/plain")],
                request_body_ref=body_ref,
                response_status=200,
                response_headers=[],
                response_body_ref=None,
                captured_at=now + timedelta(seconds=1 - index),
            )
        )

    client = TestClient(create_api(ctx))
    response = client.get("/v1/requests", params={"limit": 1})

    assert response.status_code == 200
    page = response.json()
    assert len(page) == 1
    assert page[0]["transaction_id"] == str(ids[0])
    assert page[0]["method"] == "POST"
    assert page[0]["url"] == "https://example.test/0"
    assert page[0]["request_headers"] == [
        {"name": "Content-Type", "value": "text/plain"}
    ]
    assert page[0]["request_body"] == "request-0"

    second_page = client.get("/v1/requests", params={"limit": 1, "offset": 1})
    assert second_page.status_code == 200
    assert second_page.json()[0]["transaction_id"] == str(ids[1])
