import asyncio
import json

import pytest

from obitrain.creds import CredentialStore, Credentials, profile_path

BASE = 'https://api.test'

_DEVICE_INIT = {'device_code': 'dc-secret', 'user_code': 'BCDF-2345', 'expires_in': 600, 'interval': 5}
_PENDING = {'error_code': 'authorization_pending', 'reason': 'Authorization pending'}
_TOKEN_OK = {'token': 'obt_new', 'description': 'obi CLI on host', 'created_at': '2026-01-01T00:00:00Z'}


@pytest.fixture
def no_sleep(monkeypatch):
    async def _instant(_delay):
        pass

    monkeypatch.setattr(asyncio, 'sleep', _instant)


def test_set_persists_token(store, run_cli):
    code, out, _ = run_cli('auth', 'set', 'my-token', '--base-url', BASE)

    assert code == 0
    saved = store.load()
    assert saved.access_token == 'my-token'
    assert saved.base_url == BASE
    assert json.loads(out)['status'] == 'token saved'


def test_set_isolated_by_profile(cfg_dir, run_cli):
    run_cli('auth', 'set', 'tok', '--profile', 'work', '--base-url', BASE)

    assert profile_path('work').exists()
    assert not profile_path('default').exists()


def test_clear_removes_credentials(store, run_cli):
    store.save(Credentials(access_token='tok', base_url=BASE))
    code, out, _ = run_cli('auth', 'clear')

    assert code == 0
    assert not store.path.exists()
    assert json.loads(out)['status'] == 'cleared'


def test_token_prints_only_access_token(store, run_cli):
    store.save(Credentials(access_token='secret-tok', base_url=BASE))
    code, out, _ = run_cli('auth', 'token')

    assert code == 0
    assert out.strip() == 'secret-tok'


def test_token_when_not_set_exits_auth(cfg_dir, run_cli):
    code, _, err = run_cli('auth', 'token')

    assert code == 4
    assert json.loads(err)['error'] == 'auth_required'


def test_status_reports_login_state(store, run_cli):
    store.save(Credentials(access_token='tok', base_url=BASE))
    code, out, _ = run_cli('auth', 'status', '--base-url', BASE)

    info = json.loads(out)
    assert code == 0
    assert info['logged_in'] is True
    assert info['source'] == 'file'
    assert 'access_token' not in info


def test_status_show_token(store, run_cli):
    store.save(Credentials(access_token='tok', base_url=BASE))
    _, out, _ = run_cli('auth', 'status', '--base-url', BASE, '--show-token')

    assert json.loads(out)['access_token'] == 'tok'


def test_whoami_calls_user_endpoint(stub, store, run_cli):
    store.save(Credentials(access_token='tok', base_url=BASE))
    stub.add('GET', '/v1/user', status=200, json_body={'id': 42, 'username': 'jo'})
    code, out, _ = run_cli('auth', 'whoami', '--base-url', BASE)

    assert code == 0
    assert json.loads(out) == {'id': 42, 'username': 'jo'}
    assert stub.calls('GET', '/v1/user')[0].headers['Authorization'] == 'Bearer tok'


def test_profiles_lists_known(cfg_dir, run_cli):
    CredentialStore(profile_path('alpha')).save(Credentials(access_token='x'))
    CredentialStore(profile_path('beta')).save(Credentials(access_token='y'))
    code, out, _ = run_cli('auth', 'profiles')

    payload = json.loads(out)
    assert code == 0
    assert payload['profiles'] == ['alpha', 'beta']
    assert payload['active'] == 'default'


@pytest.mark.parametrize(
    'poll_responses',
    [
        pytest.param([(200, _TOKEN_OK)], id='immediate'),
        pytest.param([(400, _PENDING), (400, _PENDING), (200, _TOKEN_OK)], id='pending-then-approved'),
        pytest.param([(400, {'error_code': 'slow_down', 'reason': 'too fast'}), (200, _TOKEN_OK)], id='slow-down'),
    ],
)
def test_login_saves_token(stub, store, run_cli, no_sleep, poll_responses):
    stub.add('POST', '/v2/user/device/code', status=200, json_body=_DEVICE_INIT)
    for status, body in poll_responses:
        stub.add('POST', '/v2/user/device/token', status=status, json_body=body)

    code, out, err = run_cli('auth', 'login', '--base-url', BASE)

    assert code == 0, err
    assert store.load().access_token == 'obt_new'
    assert json.loads(out)['status'] == 'logged in'
    assert 'BCDF-2345' in err and 'BCDF-2345' not in out
    assert len(stub.calls('POST', '/v2/user/device/token')) == len(poll_responses)
    init_body = json.loads(stub.calls('POST', '/v2/user/device/code')[0].body)
    assert init_body['description'].startswith('obi CLI on ')
    # the unauthenticated initiate request must not carry a bearer header
    assert 'Authorization' not in stub.calls('POST', '/v2/user/device/code')[0].headers
    # captured (non-TTY) stderr stays plain: no QR adornment
    assert '█' not in err and 'scan' not in err


@pytest.mark.parametrize(
    ('interactive', 'has_qr'),
    [
        pytest.param(True, True, id='tty-shows-qr'),
        pytest.param(False, False, id='piped-stays-plain'),
    ],
)
def test_login_qr_gated_on_interactive(stub, store, run_cli, no_sleep, monkeypatch, interactive, has_qr):
    monkeypatch.setattr('obitrain.auth._interactive', lambda: interactive)
    stub.add('POST', '/v2/user/device/code', status=200, json_body=_DEVICE_INIT)
    stub.add('POST', '/v2/user/device/token', status=200, json_body=_TOKEN_OK)

    code, _, err = run_cli('auth', 'login', '--base-url', BASE)

    assert code == 0
    assert ('█' in err) is has_qr
    assert ('scan the QR' in err) is has_qr
    assert 'BCDF-2345' in err  # the typed code is always shown


def test_login_interrupt_exits_cancelled(stub, store, run_cli, monkeypatch):
    async def _interrupt(_delay):
        raise KeyboardInterrupt

    monkeypatch.setattr(asyncio, 'sleep', _interrupt)
    stub.add('POST', '/v2/user/device/code', status=200, json_body=_DEVICE_INIT)

    code, _, err = run_cli('auth', 'login', '--base-url', BASE)

    assert code == 130
    assert json.loads(err.strip().splitlines()[-1])['error'] == 'cancelled'
    assert not store.path.exists()


def test_login_expired_code_exits_auth(stub, store, run_cli, no_sleep):
    stub.add('POST', '/v2/user/device/code', status=200, json_body=_DEVICE_INIT)
    stub.add('POST', '/v2/user/device/token', status=400, json_body={'error_code': 'token_expired', 'reason': 'gone'})

    code, _, err = run_cli('auth', 'login', '--base-url', BASE)

    assert code == 4
    assert json.loads(err.strip().splitlines()[-1])['error'] == 'auth_required'
    assert not store.path.exists()


def test_login_deadline_exits_auth(stub, store, run_cli, no_sleep, monkeypatch):
    clock = iter(range(0, 10_000, 400))  # each call advances 400s; deadline (600s) hit on the 2nd poll check
    monkeypatch.setattr('obitrain.auth.time', type('T', (), {'monotonic': staticmethod(lambda: next(clock))}))
    stub.add('POST', '/v2/user/device/code', status=200, json_body=_DEVICE_INIT)
    stub.add('POST', '/v2/user/device/token', status=400, json_body=_PENDING)

    code, _, err = run_cli('auth', 'login', '--base-url', BASE)

    assert code == 4
    assert 'expired' in json.loads(err.strip().splitlines()[-1])['detail']
