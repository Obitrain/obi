import asyncio
import base64
import binascii
import json
import time
from collections.abc import Mapping
from typing import Any, Self

import niquests
from filelock import FileLock

from obitrain.creds import CredentialStore, Credentials
from obitrain.errors import AuthError

# Refresh a JWT access token this many seconds before its exp claim.
_SKEW_SECONDS = 30
_REFRESH_PATH = '/v2/user/refresh'

QueryValue = str | list[str]


def new_session(base_url: str) -> niquests.AsyncSession:
    """Factory for the async HTTP session; tests monkeypatch this to mount a stub adapter."""
    return niquests.AsyncSession(base_url=base_url.rstrip('/'))


def jwt_exp(token: str) -> int | None:
    """Returns the `exp` claim of a JWT access token without verifying its signature, else None."""
    parts = token.split('.')
    if len(parts) != 3:
        return None
    payload = parts[1]
    payload += '=' * (-len(payload) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except ValueError, binascii.Error, TypeError:
        return None
    exp = claims.get('exp')
    return exp if isinstance(exp, int) else None


def read_response(resp: niquests.Response) -> tuple[int, Any, str | None]:
    """Reads a response into (status_code, json-or-text body, request id from a trace header)."""
    request_id = resp.headers.get('x-request-id') or resp.headers.get('x-trace-id') or resp.headers.get('traceparent')
    try:
        body: Any = resp.json()
    except ValueError:
        body = resp.text
    return resp.status_code or 0, body, request_id


class ObiClient:
    """Async niquests wrapper: injects bearer auth and refreshes proactively (JWT exp) and on 401.

    Single-flight refresh is enforced both in-process (an asyncio lock) and across processes (a file
    lock on the profile), so concurrent `obi` invocations rotate the refresh token without clobbering
    each other. Construct with `store=None` (e.g. for OBI_TOKEN or login flows) to disable refresh.
    """

    def __init__(self, base_url: str, creds: Credentials, store: CredentialStore | None) -> None:
        self._base_url = base_url.rstrip('/')
        self._creds = creds
        self._store = store
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> Self:
        self._http = new_session(self._base_url)
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._http.close()

    @property
    def credentials(self) -> Credentials:
        return self._creds

    @property
    def _can_refresh(self) -> bool:
        return self._store is not None and bool(self._creds.refresh_token)

    def _auth_headers(self) -> dict[str, str]:
        token = self._creds.access_token
        return {'Authorization': f'Bearer {token}'} if token else {}

    def _access_expired(self) -> bool:
        token = self._creds.access_token
        if not token:
            return False
        exp = jwt_exp(token)
        return exp is not None and time.time() >= exp - _SKEW_SECONDS

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
        """Sends the request with bearer auth; refreshes proactively on a near-expired JWT and once on 401."""
        if self._can_refresh and self._access_expired():
            await self._refresh(expected=self._creds.access_token)
        token_used = self._creds.access_token
        resp = await self._send(method, path, params, json_body, data, headers)
        if resp.status_code != 401 or not self._can_refresh:
            return resp
        await self._refresh(expected=token_used)
        return await self._send(method, path, params, json_body, data, headers)

    async def _send(
        self,
        method: str,
        path: str,
        params: Mapping[str, QueryValue] | None,
        json_body: Any,
        data: bytes | str | None,
        headers: Mapping[str, str] | None,
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

    async def refresh(self) -> Credentials:
        """Forces a token refresh and returns the rotated credentials."""
        await self._refresh(expected=self._creds.access_token)
        return self._creds

    async def _refresh(self, *, expected: str | None = None) -> None:
        """Rotates the refresh token via the API and persists the new bundle, single-flight.

        `expected` is the access token that prompted the refresh (the one that got a 401 or is near
        expiry). Concurrent callers sharing the same `expected` coalesce onto a single round-trip: the
        first rotates it, the rest see the token has already changed and return.
        """
        assert self._store is not None
        async with self._lock:
            if expected is not None and self._creds.access_token != expected:
                return  # the token we set out to refresh was already rotated
            with FileLock(str(self._store.lock_path()), timeout=30):
                disk = self._store.load()
                if disk.access_token and disk.access_token != expected and disk.refresh_token:
                    self._creds = disk  # another process already rotated; adopt its tokens
                    return
                resp = await self._http.post(_REFRESH_PATH, json={'refresh_token': self._creds.refresh_token})
                if resp.status_code != 200:
                    raise AuthError('token refresh failed; run `obi auth login`', status=resp.status_code)
                self._creds = credentials_from_bundle(resp.json(), self._base_url)
                self._store.save(self._creds)


def credentials_from_bundle(bundle: Any, base_url: str) -> Credentials:
    """Builds Credentials from a login/refresh response, raising AuthError on an unexpected shape."""
    try:
        access = bundle['access_token']
        refresh = bundle['refresh_token']
    except (KeyError, TypeError) as exc:
        raise AuthError('unexpected login response shape') from exc
    if not isinstance(access, str) or not isinstance(refresh, str):
        raise AuthError('unexpected login response shape')
    return Credentials(
        access_token=access,
        refresh_token=refresh,
        refresh_expires_at=bundle.get('refresh_expires_at'),
        base_url=base_url.rstrip('/'),
    )
