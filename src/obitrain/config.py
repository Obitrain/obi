import os
from dataclasses import dataclass

from obitrain.creds import CredentialStore, Credentials, profile_path, validate_profile

DEFAULT_BASE_URL = 'https://api.obitrain.com'


@dataclass(frozen=True)
class Config:
    """The effective configuration for a command, merged from flags, env, stored creds and defaults.

    `store` is None when the token came from --token or OBI_TOKEN — ephemeral, nothing is persisted.
    """

    base_url: str
    profile: str
    creds: Credentials
    store: CredentialStore | None

    @property
    def base_url_mismatch(self) -> bool:
        return bool(self.creds.base_url and self.creds.base_url != self.base_url)


def resolve_config(profile: str | None = None, base_url: str | None = None, token: str | None = None) -> Config:
    """Builds a Config with per-field precedence: flag > env > stored creds > default.

    A token from `--token` or OBI_TOKEN wins over stored creds and yields an ephemeral, store-less
    config (no persistence, no refresh).
    """
    prof = validate_profile(profile or os.environ.get('OBI_PROFILE') or 'default')
    store = CredentialStore(profile_path(prof))
    stored = store.load()
    resolved_base = base_url or os.environ.get('OBI_BASE_URL') or stored.base_url or DEFAULT_BASE_URL
    env_token = token or os.environ.get('OBI_TOKEN')
    if env_token:
        ephemeral = Credentials(access_token=env_token, base_url=resolved_base)
        return Config(base_url=resolved_base, profile=prof, creds=ephemeral, store=None)
    return Config(base_url=resolved_base, profile=prof, creds=stored, store=store)
