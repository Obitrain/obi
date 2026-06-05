import asyncio
import socket
import sys
import time
from typing import Any

import niquests
from piou import CommandGroup, Option

from obitrain.client import ObiClient, read_response
from obitrain.config import Config
from obitrain.creds import Credentials, list_profiles
from obitrain.errors import ApiError, AuthError, ObiError
from obitrain.options import ConfigArg, OutputOpt
from obitrain.output import (
    OutputFormat,
    agent_mode,
    render,
    render_auth_status,
    render_confirm,
    render_profiles,
    render_whoami,
)
from obitrain.runner import execute

auth_group = CommandGroup('auth', help='Authenticate with the Obitrain API.')

_WHOAMI_PATH = '/v1/user'
_DEVICE_CODE_PATH = '/v2/user/device/code'
_DEVICE_TOKEN_PATH = '/v2/user/device/token'


@auth_group.command('login', help='Log in by approving a device code in the Obitrain app.')
def login(
    description: str | None = Option(None, '--description', help='Label for the created token.'),
    config: Config = ConfigArg,
    output: OutputFormat = OutputOpt,
):
    execute(_login(config, output, description))


@auth_group.command('set', help='Store an API token generated from your Account page.')
def set_token(
    value: str = Option(..., arg_name='value'),
    config: Config = ConfigArg,
    output: OutputFormat = OutputOpt,
):
    _require_store(config)
    assert config.store is not None
    config.store.save(Credentials(access_token=value, base_url=config.base_url))
    if _pretty(output):
        render_confirm('token saved', f'profile {config.profile}', config.base_url)
    else:
        render({'status': 'token saved', 'profile': config.profile, 'base_url': config.base_url}, output)


@auth_group.command('clear', help='Remove stored credentials for the active profile.')
def clear(config: Config = ConfigArg, output: OutputFormat = OutputOpt):
    _require_store(config)
    assert config.store is not None
    config.store.clear()
    if _pretty(output):
        render_confirm('cleared', f'profile {config.profile}')
    else:
        render({'status': 'cleared', 'profile': config.profile}, output)


@auth_group.command('status', help='Show authentication status for the active profile.')
def status(
    config: Config = ConfigArg,
    show_token: bool = Option(False, '--show-token', help='Include the access token in the output.'),
    output: OutputFormat = OutputOpt,
):
    info: dict[str, Any] = {
        'profile': config.profile,
        'base_url': config.base_url,
        'logged_in': config.creds.logged_in,
        'source': 'env' if config.store is None else 'file',
        'base_url_mismatch': config.base_url_mismatch,
    }
    if show_token:
        info['access_token'] = config.creds.access_token
    if _pretty(output):
        render_auth_status(info)
    else:
        render(info, output)


@auth_group.command('whoami', help='Show the currently authenticated user.')
def whoami(config: Config = ConfigArg, output: OutputFormat = OutputOpt):
    execute(_whoami(config, output))


@auth_group.command('token', help='Print only the access token, for scripting.')
def token(config: Config = ConfigArg):
    execute(_token(config))


@auth_group.command('profiles', help='List known credential profiles.')
def profiles(config: Config = ConfigArg, output: OutputFormat = OutputOpt):
    if _pretty(output):
        render_profiles(config.profile, list_profiles())
    else:
        render({'active': config.profile, 'profiles': list_profiles()}, output)


def _pretty(output: OutputFormat) -> bool:
    return output == 'pretty' and not agent_mode()


def _require_store(config: Config) -> None:
    if config.store is None:
        raise ObiError('this profile uses an ephemeral token (--token/OBI_TOKEN); nothing to persist')


async def _login(config: Config, output: OutputFormat, description: str | None) -> int:
    _require_store(config)
    assert config.store is not None
    description = description or f'obi CLI on {socket.gethostname()}'

    async with ObiClient(config.base_url, Credentials()) as client:
        resp = await client.request('POST', _DEVICE_CODE_PATH, json_body={'description': description})
        status_code, data, request_id = read_response(resp)
        if status_code >= 400:
            raise ApiError('device code request failed', status=status_code, body=data, request_id=request_id)

        print(
            f'Open the Obitrain app on your phone: Account → Link a device, and enter this code:\n\n'
            f'    {data["user_code"]}\n\n'
            f'Waiting for approval (expires in {data["expires_in"] // 60} min, Ctrl-C to cancel)...',
            file=sys.stderr,
        )
        token = await _poll_device_token(client, data['device_code'], data['expires_in'], data['interval'])

    config.store.save(Credentials(access_token=token, base_url=config.base_url))
    if _pretty(output):
        render_confirm('logged in', f'profile {config.profile}', config.base_url)
    else:
        render({'status': 'logged in', 'profile': config.profile, 'base_url': config.base_url}, output)
    return 0


async def _poll_device_token(client: ObiClient, device_code: str, expires_in: int, interval: int) -> str:
    expired = AuthError('device code expired; run `obi auth login` again')
    deadline = time.monotonic() + expires_in
    while time.monotonic() < deadline:
        await asyncio.sleep(interval)
        try:
            resp = await client.request('POST', _DEVICE_TOKEN_PATH, json_body={'device_code': device_code})
        except (niquests.exceptions.ConnectionError, niquests.exceptions.Timeout) as exc:
            print(f'transient network error, retrying: {exc}', file=sys.stderr)
            continue
        status_code, data, request_id = read_response(resp)
        if status_code == 200:
            return data['token']
        error_code = data.get('error_code') if isinstance(data, dict) else None
        if error_code == 'authorization_pending':
            continue
        if error_code == 'slow_down':
            interval += 5
            continue
        if error_code == 'token_expired':
            raise expired
        raise ApiError('device login failed', status=status_code, body=data, request_id=request_id)
    raise expired


async def _whoami(config: Config, output: OutputFormat) -> int:
    if not config.creds.logged_in:
        raise AuthError('not logged in; run `obi auth login` (or `obi auth set <token>`)')
    async with ObiClient(config.base_url, config.creds) as client:
        resp = await client.request('GET', _WHOAMI_PATH)
        status_code, data, request_id = read_response(resp)
    if status_code >= 400:
        raise ApiError('whoami failed', status=status_code, body=data, request_id=request_id)
    if _pretty(output):
        from obitrain.api.schema import annotate_enums

        render_whoami(annotate_enums(data, 'GET', _WHOAMI_PATH))
        return 0
    render(data, output)
    return 0


async def _token(config: Config) -> int:
    if not config.creds.access_token:
        raise AuthError('not logged in; run `obi auth login` (or `obi auth set <token>`)')
    print(config.creds.access_token)
    return 0
