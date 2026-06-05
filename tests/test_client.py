from obitrain.client import ObiClient, read_response
from obitrain.creds import Credentials

BASE = 'https://api.test'


async def test_bearer_is_injected(stub, store):
    store.save(Credentials(access_token='tok', base_url=BASE))
    stub.add('GET', '/v1/me', status=200, json_body={'id': 1})

    async with ObiClient(BASE, store.load()) as client:
        resp = await client.request('GET', '/v1/me')

    assert resp.status_code == 200
    assert stub.calls('GET', '/v1/me')[0].headers['Authorization'] == 'Bearer tok'


async def test_no_token_omits_auth_header(stub):
    stub.add('GET', '/health', status=200, json_body={'up': True})

    async with ObiClient(BASE, Credentials()) as client:
        await client.request('GET', '/health')

    assert 'Authorization' not in stub.calls('GET', '/health')[0].headers


async def test_401_is_surfaced_without_retry(stub, store):
    store.save(Credentials(access_token='tok', base_url=BASE))
    stub.add('GET', '/v1/me', status=401, json_body={'detail': 'unauthorized'})

    async with ObiClient(BASE, store.load()) as client:
        resp = await client.request('GET', '/v1/me')

    assert resp.status_code == 401
    assert len(stub.calls('GET', '/v1/me')) == 1


def test_read_response_parses_json():
    import niquests
    from niquests.structures import CaseInsensitiveDict

    resp = niquests.Response()
    resp.status_code = 200
    resp._content = b'{"ok": true}'
    resp.headers = CaseInsensitiveDict({'Content-Type': 'application/json', 'x-request-id': 'abc'})

    status, body, request_id = read_response(resp)
    assert (status, body, request_id) == (200, {'ok': True}, 'abc')
