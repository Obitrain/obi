import json


from obitrain.creds import CredentialStore, Credentials, profile_path

BASE = 'https://api.test'
BUNDLE = {
    'access_token': 'a1',
    'token_type': 'bearer',
    'refresh_token': 'r1',
    'refresh_expires_at': '2027-01-01T00:00:00Z',
}


def test_login_persists_credentials(stub, store, run_cli):
    stub.add('POST', '/v2/user/login', status=200, json_body=BUNDLE)
    code, out, _ = run_cli('auth', 'login', '--base-url', BASE, '--email', 'a@b.c', '--password', 'pw')

    assert code == 0
    saved = store.load()
    assert (saved.access_token, saved.refresh_token, saved.base_url) == ('a1', 'r1', BASE)
    assert json.loads(out)['status'] == 'logged in'
    assert json.loads(stub.calls('POST', '/v2/user/login')[0].body) == {
        'email': 'a@b.c',
        'username': None,
        'password': 'pw',
    }


def test_login_failure_maps_to_http_exit(stub, store, run_cli):
    stub.add('POST', '/v2/user/login', status=401, json_body={'detail': 'bad creds'})
    code, _, err = run_cli('auth', 'login', '--base-url', BASE, '--email', 'a@b.c', '--password', 'wrong')

    assert code == 7
    assert json.loads(err)['status'] == 401
    assert not store.path.exists()


def test_profiles_are_isolated(stub, cfg_dir, run_cli):
    stub.add('POST', '/v2/user/login', status=200, json_body=BUNDLE)
    run_cli('auth', 'login', '--profile', 'work', '--base-url', BASE, '--email', 'a@b.c', '--password', 'pw')

    assert profile_path('work').exists()
    assert not profile_path('default').exists()


def test_token_prints_only_access_token(store, run_cli):
    store.save(Credentials(access_token='secret-tok', refresh_token='r1', base_url=BASE))
    code, out, _ = run_cli('auth', 'token')

    assert code == 0
    assert out.strip() == 'secret-tok'


def test_token_when_logged_out_exits_auth(cfg_dir, run_cli):
    code, _, err = run_cli('auth', 'token')

    assert code == 4
    assert json.loads(err)['error'] == 'auth_required'


def test_logout_clears_credentials(stub, store, run_cli):
    store.save(Credentials(access_token='a1', refresh_token='r1', base_url=BASE))
    stub.add('POST', '/v2/user/logout', status=200, json_body={})
    code, _, _ = run_cli('auth', 'logout', '--base-url', BASE)

    assert code == 0
    assert not store.path.exists()
    assert json.loads(stub.calls('POST', '/v2/user/logout')[0].body) == {'refresh_token': 'r1'}


def test_status_reports_login_state(store, run_cli):
    store.save(Credentials(access_token='a1', refresh_token='r1', base_url=BASE, refresh_expires_at='2027-01-01'))
    code, out, _ = run_cli('auth', 'status', '--base-url', BASE)

    info = json.loads(out)
    assert code == 0
    assert info['logged_in'] is True
    assert info['source'] == 'file'
    assert 'access_token' not in info


def test_status_show_token(store, run_cli):
    store.save(Credentials(access_token='a1', refresh_token='r1', base_url=BASE))
    _, out, _ = run_cli('auth', 'status', '--base-url', BASE, '--show-token')
    assert json.loads(out)['access_token'] == 'a1'


def test_whoami_calls_user_endpoint(stub, store, run_cli):
    store.save(Credentials(access_token='a1', refresh_token='r1', base_url=BASE))
    stub.add('GET', '/v1/user', status=200, json_body={'id': 42, 'username': 'jo'})
    code, out, _ = run_cli('auth', 'whoami', '--base-url', BASE)

    assert code == 0
    assert json.loads(out) == {'id': 42, 'username': 'jo'}
    assert stub.calls('GET', '/v1/user')[0].headers['Authorization'] == 'Bearer a1'


def test_profiles_lists_known(cfg_dir, run_cli):
    CredentialStore(profile_path('alpha')).save(Credentials(access_token='x'))
    CredentialStore(profile_path('beta')).save(Credentials(access_token='y'))
    code, out, _ = run_cli('auth', 'profiles')

    payload = json.loads(out)
    assert code == 0
    assert payload['profiles'] == ['alpha', 'beta']
    assert payload['active'] == 'default'
