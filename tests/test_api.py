import io
import json

import pytest

from obitrain.creds import Credentials

BASE = 'https://api.test'


@pytest.fixture
def logged_in(store):
    store.save(Credentials(access_token='tok', base_url=BASE))
    return store


def test_get_sends_bearer_and_query(stub, logged_in, run_cli):
    stub.add('GET', '/v1/x', status=200, json_body={'ok': 1})
    code, out, err = run_cli('api', '/v1/x', '--base-url', BASE, '-q', 'limit=10', 'size=2')

    assert code == 0
    assert json.loads(out) == {'ok': 1}
    sent = stub.calls('GET', '/v1/x')[0]
    assert sent.headers['Authorization'] == 'Bearer tok'
    assert 'limit=10' in (sent.url or '') and 'size=2' in (sent.url or '')


def test_data_implies_post_with_json_body(stub, logged_in, run_cli):
    stub.add('POST', '/v1/x', status=201, json_body={'created': True})
    code, out, _ = run_cli('api', '/v1/x', '--base-url', BASE, '-d', '{"a": 1}')

    assert code == 0
    sent = stub.calls('POST', '/v1/x')[0]
    assert json.loads(sent.body) == {'a': 1}
    assert sent.headers['Content-Type'].startswith('application/json')


def test_body_from_stdin(stub, logged_in, run_cli, monkeypatch):
    stub.add('POST', '/v1/x', status=200, json_body={'ok': 1})
    monkeypatch.setattr('sys.stdin', io.StringIO('{"from": "stdin"}'))
    code, _, _ = run_cli('api', '/v1/x', '--base-url', BASE, '-X', 'POST', '-d', '@-')

    assert code == 0
    assert json.loads(stub.calls('POST', '/v1/x')[0].body) == {'from': 'stdin'}


def test_dry_run_sends_nothing(stub, logged_in, run_cli):
    code, out, _ = run_cli('api', '/v1/x', '--base-url', BASE, '-q', 'a=1', '-n')

    assert code == 0
    payload = json.loads(out)
    assert payload['method'] == 'GET'
    assert payload['url'] == f'{BASE}/v1/x'
    assert payload['headers']['Authorization'] == 'Bearer …'  # redacted
    assert stub.requests == []


@pytest.mark.parametrize(
    ('status', 'expected_code'),
    [
        pytest.param(404, 7, id='not-found'),
        pytest.param(500, 6, id='server-error'),
    ],
)
def test_error_status_maps_to_exit_code(stub, logged_in, run_cli, status, expected_code):
    stub.add('GET', '/v1/x', status=status, json_body={'detail': 'boom'})
    code, out, err = run_cli('api', '/v1/x', '--base-url', BASE)

    assert code == expected_code
    assert json.loads(out) == {'detail': 'boom'}  # body still rendered to stdout
    assert json.loads(err)['error'] == 'http_error'


def test_unauthorized_surfaces_auth_error(stub, cfg_dir, run_cli):
    stub.add('GET', '/v1/x', status=401, json_body={'detail': 'nope'})
    code, out, err = run_cli('api', '/v1/x', '--base-url', BASE, '--token', 'ephemeral')

    assert code == 4
    assert json.loads(out) == {'detail': 'nope'}
    assert json.loads(err)['error'] == 'auth_required'


def test_429_surfaces_retry_after(stub, logged_in, run_cli):
    stub.add('GET', '/v1/x', status=429, json_body={'detail': 'slow down'}, headers={'Retry-After': '12'})
    code, _, err = run_cli('api', '/v1/x', '--base-url', BASE)

    assert code == 7
    assert json.loads(err)['retry_after'] == '12'


@pytest.mark.parametrize(
    ('pair', 'expected_code'),
    [
        pytest.param('limit=10', 0, id='valid'),
        pytest.param('limit', 1, id='missing-sep'),
    ],
)
def test_query_validation(stub, logged_in, run_cli, pair, expected_code):
    stub.add('GET', '/v1/x', status=200, json_body={})
    code, _, _ = run_cli('api', '/v1/x', '--base-url', BASE, '-q', pair)
    assert code == expected_code
