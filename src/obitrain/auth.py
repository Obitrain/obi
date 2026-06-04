import getpass
import sys
from collections.abc import Mapping
from typing import Any

import niquests
from piou import CommandGroup, Option

from obitrain.client import ObiClient, credentials_from_bundle, read_response
from obitrain.config import Config
from obitrain.creds import Credentials, list_profiles
from obitrain.errors import ApiError, AuthError, ObiError
from obitrain.options import ConfigArg, OutputOpt
from obitrain.output import OutputFormat, render
from obitrain.runner import execute

auth_group = CommandGroup('auth', help='Authenticate with the Obitrain API.')

_WHOAMI_PATH = '/v1/user'


@auth_group.command('login', help='Log in with email/username and password.')
def login(
    config: Config = ConfigArg,
    email: str | None = Option(None, '--email', help='Account email.'),
    username: str | None = Option(None, '--username', help='Account username.'),
    password: str | None = Option(None, '--password', help='Account password (prompted if omitted).'),
    force: bool = Option(False, '--force', help='Re-authenticate even if already logged in.'),
    yes: bool = Option(False, '--yes', help='Non-interactive: never prompt.'),
    output: OutputFormat = OutputOpt,
):
    secret = _resolve_password(password, yes)
    body = {'email': email, 'username': username, 'password': secret}
    execute(_login(config, '/v2/user/login', body, output, force=force))


@auth_group.command('login-token', help='Log in with a one-time login token.')
def login_token(
    token: str = Option(..., '--token-value', help='The login token.'),
    config: Config = ConfigArg,
    force: bool = Option(False, '--force'),
    output: OutputFormat = OutputOpt,
):
    execute(_login(config, '/v2/user/login/token', {'token': token}, output, force=force))


@auth_group.command('login-google', help='Log in with a Google ID token.')
def login_google(
    token: str = Option(..., '--token-value', help='Google ID token.'),
    config: Config = ConfigArg,
    lang: str | None = Option(None, '--lang'),
    force: bool = Option(False, '--force'),
    output: OutputFormat = OutputOpt,
):
    execute(_login(config, '/v2/user/login/google', {'token': token, 'lang': lang}, output, force=force))


@auth_group.command('login-facebook', help='Log in with a Facebook access token.')
def login_facebook(
    token: str = Option(..., '--token-value', help='Facebook access token.'),
    config: Config = ConfigArg,
    force: bool = Option(False, '--force'),
    output: OutputFormat = OutputOpt,
):
    execute(_login(config, '/v2/user/login/facebook', {'token': token}, output, force=force))


@auth_group.command('login-apple', help='Log in with an Apple identity token.')
def login_apple(
    token: str = Option(..., '--token-value', help='Apple identity token.'),
    config: Config = ConfigArg,
    force: bool = Option(False, '--force'),
    output: OutputFormat = OutputOpt,
):
    execute(_login(config, '/v2/user/login/apple', {'token': token}, output, force=force))


@auth_group.command('register', help='Create a new account and log in.')
def register(
    config: Config = ConfigArg,
    email: str = Option(..., '--email'),
    username: str = Option(..., '--username'),
    password: str | None = Option(None, '--password', help='Password (prompted if omitted).'),
    yes: bool = Option(False, '--yes'),
    output: OutputFormat = OutputOpt,
):
    secret = _resolve_password(password, yes)
    body = {'email': email, 'username': username, 'password': secret}
    execute(_login(config, '/v2/user/register', body, output, force=True))


@auth_group.command('refresh', help='Rotate the refresh token and store a new access token.')
def refresh(
    config: Config = ConfigArg,
    force: bool = Option(False, '--force', help='Refresh even if the base URL differs from the stored one.'),
    output: OutputFormat = OutputOpt,
):
    execute(_refresh(config, force, output))


@auth_group.command('logout', help='Revoke the refresh token and clear stored credentials.')
def logout(config: Config = ConfigArg, output: OutputFormat = OutputOpt):
    execute(_logout(config, output))


@auth_group.command('status', help='Show authentication status for the active profile.')
def status(
    config: Config = ConfigArg,
    show_token: bool = Option(False, '--show-token', help='Include the access token in the output.'),
    fresh: bool = Option(False, '--fresh', help='Refresh the token before reporting.'),
    output: OutputFormat = OutputOpt,
):
    execute(_status(config, show_token, fresh, output))


@auth_group.command('whoami', help='Show the currently authenticated user.')
def whoami(
    config: Config = ConfigArg,
    fresh: bool = Option(False, '--fresh', help='Refresh the token before the call.'),
    output: OutputFormat = OutputOpt,
):
    execute(_whoami(config, fresh, output))


@auth_group.command('token', help='Print only the access token, for scripting.')
def token(config: Config = ConfigArg):
    execute(_token(config))


@auth_group.command('profiles', help='List known credential profiles.')
def profiles(config: Config = ConfigArg, output: OutputFormat = OutputOpt):
    execute(_profiles(config, output))


def _resolve_password(password: str | None, yes: bool) -> str:
    if password is not None:
        return password
    if yes or not sys.stdin.isatty():
        raise ObiError('password required; pass --password or run interactively')
    return getpass.getpass('Password: ')


def _require_store(config: Config) -> None:
    if config.store is None:
        raise ObiError('this profile uses an ephemeral token (--token/OBI_TOKEN); nothing to persist')


async def _post_unauthenticated(config: Config, path: str, body: Mapping[str, Any]) -> tuple[int, Any, str | None]:
    async with ObiClient(config.base_url, Credentials(), store=None) as client:
        resp = await client.request('POST', path, json_body=dict(body))
        return read_response(resp)


async def _login(config: Config, path: str, body: Mapping[str, Any], output: OutputFormat, *, force: bool) -> int:
    _require_store(config)
    assert config.store is not None
    if config.creds.logged_in and not force:
        raise ObiError('already logged in; pass --force to re-authenticate')
    status_code, data, request_id = await _post_unauthenticated(config, path, body)
    if status_code >= 400:
        raise ApiError(f'login failed at {path}', status=status_code, body=data, request_id=request_id)
    config.store.save(credentials_from_bundle(data, config.base_url))
    render({'status': 'logged in', 'profile': config.profile, 'base_url': config.base_url}, output)
    return 0


async def _refresh(config: Config, force: bool, output: OutputFormat) -> int:
    if not config.refreshable:
        raise AuthError('not logged in; run `obi auth login`')
    if config.base_url_mismatch and not force:
        raise ObiError(
            f'stored credentials were minted for {config.creds.base_url!r}, not {config.base_url!r}; '
            'pass --force to refresh anyway'
        )
    async with ObiClient(config.base_url, config.creds, config.store) as client:
        creds = await client.refresh()
    render(
        {'status': 'refreshed', 'profile': config.profile, 'refresh_expires_at': creds.refresh_expires_at},
        output,
    )
    return 0


async def _logout(config: Config, output: OutputFormat) -> int:
    _require_store(config)
    assert config.store is not None
    refresh_token = config.creds.refresh_token
    if refresh_token:
        try:
            async with ObiClient(config.base_url, Credentials(), store=None) as client:
                await client.request('POST', '/v2/user/logout', json_body={'refresh_token': refresh_token})
        except niquests.exceptions.RequestException:
            pass  # best-effort; the server logout is idempotent
    config.store.clear()
    render({'status': 'logged out', 'profile': config.profile}, output)
    return 0


async def _status(config: Config, show_token: bool, fresh: bool, output: OutputFormat) -> int:
    if fresh and config.refreshable:
        async with ObiClient(config.base_url, config.creds, config.store) as client:
            await client.refresh()
    creds = config.store.load() if config.store is not None else config.creds
    info: dict[str, Any] = {
        'profile': config.profile,
        'base_url': config.base_url,
        'logged_in': creds.logged_in,
        'refresh_expires_at': creds.refresh_expires_at,
        'source': 'env' if config.store is None else 'file',
        'base_url_mismatch': config.base_url_mismatch,
    }
    if show_token:
        info['access_token'] = creds.access_token
    render(info, output)
    return 0


async def _whoami(config: Config, fresh: bool, output: OutputFormat) -> int:
    if not config.creds.logged_in:
        raise AuthError('not logged in; run `obi auth login`')
    if fresh and config.refreshable:
        async with ObiClient(config.base_url, config.creds, config.store) as refresher:
            await refresher.refresh()
    async with ObiClient(config.base_url, config.creds, config.store) as client:
        resp = await client.request('GET', _WHOAMI_PATH)
        status_code, data, request_id = read_response(resp)
    if status_code >= 400:
        raise ApiError('whoami failed', status=status_code, body=data, request_id=request_id)
    render(data, output)
    return 0


async def _token(config: Config) -> int:
    if not config.creds.access_token:
        raise AuthError('not logged in; run `obi auth login`')
    print(config.creds.access_token)
    return 0


async def _profiles(config: Config, output: OutputFormat) -> int:
    render({'active': config.profile, 'profiles': list_profiles()}, output)
    return 0
