import json
import stat
from contextlib import nullcontext

import pytest

from obitrain.creds import CredentialStore, Credentials, config_dir, list_profiles, profile_path, validate_profile
from obitrain.errors import ObiError


def test_save_load_roundtrip(store):
    creds = Credentials(access_token='a', refresh_token='r', refresh_expires_at='2027', base_url='https://x')
    store.save(creds)
    assert store.load() == creds


def test_saved_file_is_0600(store):
    store.save(Credentials(access_token='a'))
    mode = stat.S_IMODE(store.path.stat().st_mode)
    assert mode == 0o600


def test_load_missing_returns_empty(store):
    assert store.load() == Credentials()


def test_load_ignores_unknown_keys(store):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps({'access_token': 'a', 'bogus': 1}))
    assert store.load().access_token == 'a'


def test_clear_removes_file(store):
    store.save(Credentials(access_token='a'))
    store.clear()
    store.clear()  # idempotent
    assert not store.path.exists()


def test_list_profiles(cfg_dir):
    assert list_profiles() == []
    CredentialStore(profile_path('beta')).save(Credentials(access_token='b'))
    CredentialStore(profile_path('alpha')).save(Credentials(access_token='a'))
    assert list_profiles() == ['alpha', 'beta']


def test_config_dir_override(cfg_dir):
    assert config_dir() == cfg_dir


@pytest.mark.parametrize(
    ('name', 'ctx'),
    [
        pytest.param('default', nullcontext(), id='simple'),
        pytest.param('work.2-prod_x', nullcontext(), id='allowed-charset'),
        pytest.param('../escape', pytest.raises(ObiError), id='traversal'),
        pytest.param('with space', pytest.raises(ObiError), id='space'),
    ],
)
def test_validate_profile(name, ctx):
    with ctx:
        assert validate_profile(name) == name
