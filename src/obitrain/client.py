from collections.abc import Mapping
from typing import Any, Self

import niquests

from obitrain.creds import Credentials

QueryValue = str | list[str]


def new_session(base_url: str) -> niquests.AsyncSession:
    """Factory for the async HTTP session; tests monkeypatch this to mount a stub adapter."""
    return niquests.AsyncSession(base_url=base_url.rstrip('/'))


def read_response(resp: niquests.Response) -> tuple[int, Any, str | None]:
    """Reads a response into (status_code, json-or-text body, request id from a trace header)."""
    request_id = resp.headers.get('x-request-id') or resp.headers.get('x-trace-id') or resp.headers.get('traceparent')
    try:
        body: Any = resp.json()
    except ValueError:
        body = resp.text
    return resp.status_code or 0, body, request_id


class ObiClient:
    """Async niquests wrapper: injects bearer auth on every request."""

    def __init__(self, base_url: str, creds: Credentials) -> None:
        self._base_url = base_url.rstrip('/')
        self._creds = creds

    async def __aenter__(self) -> Self:
        self._http = new_session(self._base_url)
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.close()

    def _auth_headers(self) -> dict[str, str]:
        token = self._creds.access_token
        return {'Authorization': f'Bearer {token}'} if token else {}

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
        json_body: Any = None,
        data: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> niquests.Response:
        merged = {**self._auth_headers(), **(headers or {})}
        return await self._http.request(
            method.upper(),
            path,
            params=dict(params) if params else None,
            json=json_body,
            data=data,
            headers=merged,
        )
