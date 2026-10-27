from __future__ import annotations

import base64
from urllib.parse import urlparse

from proxy_as_code.capture.models import HeaderPair, OriginalRecord
from proxy_as_code.compiler.manifest import slug_from_path


def _repr_body(content: bytes | None) -> str:
    if not content:
        return "None"
    try:
        text = content.decode("utf-8")
        if "\x00" not in text:
            return repr(text)
    except UnicodeDecodeError:
        pass
    b64 = base64.b64encode(content).decode("ascii")
    return f"base64.b64decode({b64!r})"


def _headers_dict(headers: list[HeaderPair], for_export: bool) -> str:
    items = []
    for h in headers:
        name = h.name
        value = h.value
        if for_export and name.lower() == "authorization" and value.lower().startswith("bearer "):
            items.append(f'            "{name}": f"Bearer {{token}}",')
        elif for_export and name.lower() == "host":
            continue
        else:
            items.append(f'            "{name}": {value!r},')
    if not items:
        return "{}"
    inner = "\n".join(items)
    return "{\n" + inner + "\n        }"


def compile_python(record: OriginalRecord, body: bytes | None) -> str:
    parsed = urlparse(record.url)
    base_hint = f"{parsed.scheme}://{parsed.netloc}"
    fn_name = f"replay_{slug_from_path(record.path)}"
    headers_block = _headers_dict(record.request_headers, for_export=True)
    body_expr = _repr_body(body)
    path_with_query = record.path + (f"?{record.query}" if record.query else "")

    return f'''import base64
import httpx


def {fn_name}(base_url: str, token: str | None = None) -> httpx.Response:
    """Semantic replay of {record.method} {path_with_query} (transaction {record.id})."""
    headers = {headers_block}
    if token and "Authorization" in headers:
        headers["Authorization"] = f"Bearer {{token}}"
    url = f"{{base_url.rstrip('/')}}{path_with_query}"
    content = {body_expr}
    with httpx.Client(timeout=15.0) as client:
        return client.request(
            {record.method!r},
            url,
            headers=headers,
            content=content,
        )


# Suggested base URL from capture: {base_hint}
'''
