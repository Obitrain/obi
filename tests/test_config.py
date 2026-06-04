from contextlib import nullcontext

import pytest

from obitrain.config import DEFAULT_BASE_URL, resolve_config
from obitrain.creds import CredentialStore, Credentials, profile_path
from obitrain.errors import ObiError


def test_default_base_url(cfg_dir):
    assert resolve_config().base_url == DEFAULT_BASE_URL


def test_flag_beats_env_and_stored(cfg_dir, monkeypatch):
    CredentialStore(profile_path('default')).save(Credentials(base_url='https://stored'))
    monkeypatch.setenv('OBI_BASE_URL', 'https://env')
    assert resolve_config(base_url='https://flag').base_url == 'https://flag'


def test_env_beats_stored(cfg_dir, monkeypatch):
    CredentialStore(profile_path('default')).save(Credentials(base_url='https://stored'))
    monkeypatch.setenv('OBI_BASE_URL', 'https://env')
    assert resolve_config().base_url == 'https://env'


def test_stored_base_url_used_when_no_flag_or_env(cfg_dir):
    CredentialStore(profile_path('default')).save(Credentials(base_url='https://stored'))
    assert resolve_config().base_url == 'https://stored'


def test_token_is_ephemeral_and_storeless(cfg_dir, monkeypatch):
    monkeypatch.setenv('OBI_TOKEN', 'envtok')
    cfg = resolve_config()
    assert cfg.store is None
    assert cfg.creds.access_token == 'envtok'


def test_profile_from_env(cfg_dir, monkeypatch):
    monkeypatch.setenv('OBI_PROFILE', 'work')
    assert resolve_config().profile == 'work'


def test_base_url_mismatch_detected(cfg_dir):
    CredentialStore(profile_path('default')).save(Credentials(access_token='a', base_url='https://one'))
    assert resolve_config(base_url='https://two').base_url_mismatch is True


@pytest.mark.parametrize(
    ('profile', 'ctx'),
    [
        pytest.param('work', nullcontext(), id='valid'),
        pytest.param('../escape', pytest.raises(ObiError), id='traversal'),
    ],
)
def test_profile_name_validation(cfg_dir, profile, ctx):
    with ctx:
        resolve_config(profile=profile)
