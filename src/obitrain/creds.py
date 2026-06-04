import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from obitrain.errors import ObiError

_PROFILE_RE = re.compile(r'^[A-Za-z0-9._-]+$')


@dataclass
class Credentials:
    """The persisted auth state for one profile.

    There is intentionally no access-token expiry field: the Obitrain login/refresh response carries
    only `refresh_expires_at`, so the client refreshes reactively on 401 (and proactively when the
    access token is a decodable JWT). `base_url` records the host that minted these tokens so we never
    send a refresh token to a different environment.
    """

    access_token: str | None = None
    refresh_token: str | None = None
    refresh_expires_at: str | None = None
    base_url: str | None = None

    @property
    def logged_in(self) -> bool:
        return bool(self.access_token)


def config_dir() -> Path:
    """Resolves the config directory: OBI_CONFIG_DIR, then XDG_CONFIG_HOME/obi, then ~/.config/obi."""
    if override := os.environ.get('OBI_CONFIG_DIR'):
        return Path(override)
    if xdg := os.environ.get('XDG_CONFIG_HOME'):
        return Path(xdg) / 'obi'
    return Path.home() / '.config' / 'obi'


def validate_profile(name: str) -> str:
    """Validates a profile name against a strict charset to avoid path traversal and odd filenames."""
    if not _PROFILE_RE.match(name):
        raise ObiError(f'invalid profile name {name!r}; allowed characters: A-Z a-z 0-9 . _ -')
    return name


def profile_path(profile: str) -> Path:
    return config_dir() / 'profiles' / f'{validate_profile(profile)}.json'


def list_profiles() -> list[str]:
    profiles = config_dir() / 'profiles'
    if not profiles.is_dir():
        return []
    return sorted(p.stem for p in profiles.glob('*.json'))


class CredentialStore:
    """Loads and atomically persists one profile's credentials as a 0600 JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Credentials:
        try:
            data = json.loads(self.path.read_text())
        except OSError, ValueError:
            return Credentials()
        known = {f.name for f in fields(Credentials)}
        return Credentials(**{k: v for k, v in data.items() if k in known})

    def save(self, creds: Credentials) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix='.cred-', suffix='.tmp')
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'w') as f:
                json.dump(asdict(creds), f, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)

    def lock_path(self) -> Path:
        return self.path.with_suffix('.lock')
