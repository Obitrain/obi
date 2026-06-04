import asyncio
from contextlib import nullcontext

import pytest

from obitrain.client import ObiClient, read_response
from obitrain.creds import Credentials
from obitrain.errors import AuthError

BASE = 'https://api.test'
NEW_BUNDLE = {
    'access_token': 'new',
    'token_type': 'bearer',
    'refresh_token': 'r2',
    'refresh_expires_at': '2027-01-01T00:00:00Z',
}


async def test_refresh_on_401_persists_rotated_tokens(stub, store):
    store.save(Credentials(access_token='old', refresh_token='r1', base_url=BASE))
    stub.add('GET', '/v1/me', status=401)
    stub.add('GET', '/v1/me', status=200, json_body={'id': 1})
    stub.add('POST', '/v2/user/refresh', status=200, json_body=NEW_BUNDLE)

    async with ObiClient(BASE, store.load(), store) as client:
        resp = await client.request('GET', '/v1/me')
        status, body, _ = read_response(resp)

    assert (status, body) == (200, {'id': 1})
    assert store.load().access_token == 'new'
    assert store.load().refresh_token == 'r2'
    assert stub.calls('GET', '/v1/me')[1].headers['Authorization'] == 'Bearer new'


async def test_no_refresh_token_surfaces_401(stub, store):
    stub.add('GET', '/v1/me', status=401, json_body={'detail': 'unauthorized'})
    async with ObiClient(BASE, Credentials(access_token='only'), store) as client:
        resp = await client.request('GET', '/v1/me')
    assert resp.status_code == 401
    assert stub.calls('POST', '/v2/user/refresh') == []


async def test_single_flight_coalesces_concurrent_refreshes(stub, store):
    # Two callers holding the same stale token must share a single refresh round-trip.
    store.save(Credentials(access_token='old', refresh_token='r1', base_url=BASE))
    stub.add('POST', '/v2/user/refresh', status=200, json_body=NEW_BUNDLE)

    async with ObiClient(BASE, store.load(), store) as client:
        await asyncio.gather(client._refresh(expected='old'), client._refresh(expected='old'))

    assert len(stub.calls('POST', '/v2/user/refresh')) == 1
    assert client.credentials.access_token == 'new'


@pytest.mark.parametrize(
    ('refresh_status', 'bundle', 'ctx'),
    [
        pytest.param(200, NEW_BUNDLE, nullcontext(), id='refresh-ok'),
        pytest.param(401, {'detail': 'revoked'}, pytest.raises(AuthError), id='refresh-revoked'),
        pytest.param(200, {'token_type': 'bearer'}, pytest.raises(AuthError), id='refresh-bad-shape'),
    ],
)
async def test_refresh_failure_modes(stub, store, refresh_status, bundle, ctx):
    store.save(Credentials(access_token='old', refresh_token='r1', base_url=BASE))
    stub.add('GET', '/v1/me', status=401)
    stub.add('GET', '/v1/me', status=200, json_body={'id': 1})
    stub.add('POST', '/v2/user/refresh', status=refresh_status, json_body=bundle)

    async with ObiClient(BASE, store.load(), store) as client:
        with ctx:
            await client.request('GET', '/v1/me')
