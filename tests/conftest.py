import json
from collections import defaultdict, deque
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

import niquests
import pytest
from niquests import PreparedRequest, Response
from niquests.adapters import AsyncBaseAdapter
from niquests.structures import CaseInsensitiveDict

from obitrain import client as client_mod
from obitrain.creds import CredentialStore, profile_path


class _StubRaw:
    """Minimal stand-in for a urllib3 response; satisfies niquests' cookie extraction (which no-ops)."""

    def release_conn(self) -> None:
        pass

    def close(self) -> None:
        pass


class StubAdapter(AsyncBaseAdapter):
    """A niquests adapter that returns canned responses and records the requests it received.

    Routes are keyed by (method, path); register several responses for one route to have them returned
    in order (the last registered response repeats for any further calls).
    """

    def __init__(self) -> None:
        super().__init__()
        self.routes: dict[tuple[str, str], deque[tuple[int, bytes, dict[str, str]]]] = defaultdict(deque)
        self.requests: list[PreparedRequest] = []

    def add(
        self,
        method: str,
        path: str,
        *,
        status: int = 200,
        json_body: Any = None,
        text: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> 'StubAdapter':
        if text is not None:
            body = text.encode()
        elif json_body is not None:
            body = json.dumps(json_body).encode()
        else:
            body = b''
        self.routes[(method.upper(), path)].append((status, body, dict(headers or {})))
        return self

    def calls(self, method: str, path: str) -> list[PreparedRequest]:
        return [r for r in self.requests if r.method == method.upper() and urlsplit(r.url).path == path]

    async def send(self, request: PreparedRequest, *args: Any, **kwargs: Any) -> Response:  # type: ignore[override]
        self.requests.append(request)
        queue = self.routes.get((request.method or '', urlsplit(request.url or '').path))
        if not queue:
            return self._build(request, 404, json.dumps({'detail': 'no stub registered'}).encode(), {})
        status, body, headers = queue[0] if len(queue) == 1 else queue.popleft()
        return self._build(request, status, body, headers)

    def _build(self, request: PreparedRequest, status: int, body: bytes, headers: dict[str, str]) -> Response:
        resp = Response()
        resp.status_code = status
        resp._content = body
        resp.url = request.url or ''
        resp.request = request
        resp.headers = CaseInsensitiveDict({'Content-Type': 'application/json', **headers})
        resp.raw = _StubRaw()  # non-None, no _original_response -> cookie extraction no-ops
        resp.reason = ''
        return resp

    async def close(self) -> None:
        pass


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch) -> Any:
    monkeypatch.setenv('OBI_CONFIG_DIR', str(tmp_path))
    for var in ('OBI_BASE_URL', 'OBI_TOKEN', 'OBI_PROFILE', 'NO_COLOR'):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


@pytest.fixture
def store(cfg_dir) -> CredentialStore:
    return CredentialStore(profile_path('default'))


@pytest.fixture
def run_cli(capsys):
    """Invokes the CLI with argv, returning (exit_code, stdout, stderr)."""
    from obitrain.run import cli

    def invoke(*argv: str) -> tuple[int, str, str]:
        code = 0
        try:
            cli.run_with_args(*argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return invoke


@pytest.fixture
def stub(monkeypatch) -> StubAdapter:
    adapter = StubAdapter()

    def factory(base_url: str) -> niquests.AsyncSession:
        session = niquests.AsyncSession(base_url=base_url.rstrip('/'))
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    monkeypatch.setattr(client_mod, 'new_session', factory)
    return adapter
