import io
import json

import pytest
import yaml
from rich.console import Console

from obitrain.options import _resolve_output
from obitrain.output import (
    agent_mode,
    device_link_qr,
    render,
    render_auth_status,
    render_confirm,
    render_error,
    render_operation,
    render_profiles,
    render_whoami,
)


@pytest.mark.parametrize(
    ('output', 'as_json', 'expected'),
    [
        pytest.param(None, False, 'pretty', id='default-pretty'),
        pytest.param(None, True, 'json', id='json-flag'),
        pytest.param('yaml', False, 'yaml', id='explicit-output'),
        pytest.param('yaml', True, 'yaml', id='explicit-output-wins-over-json-flag'),
    ],
)
def test_resolve_output(output, as_json, expected):
    assert _resolve_output(output, as_json) == expected


def test_render_json():
    out = io.StringIO()
    render({'a': 1, 'é': 'x'}, 'json', stream=out)
    assert json.loads(out.getvalue()) == {'a': 1, 'é': 'x'}


def test_render_yaml():
    out = io.StringIO()
    render({'a': [1, 2]}, 'yaml', stream=out)
    assert yaml.safe_load(out.getvalue()) == {'a': [1, 2]}


def test_render_raw_passthrough():
    out = io.StringIO()
    render('plain text', 'raw', stream=out)
    assert out.getvalue() == 'plain text\n'


def test_render_error_to_stderr(capsys):
    render_error('http_error', status=404, request_id='abc', retry_after=None)
    err = json.loads(capsys.readouterr().err)
    assert err == {'error': 'http_error', 'status': 404, 'request_id': 'abc'}  # None dropped


_WHOAMI_USER = {
    'email': 'julien@example.com',
    'username': 'julien',
    'country': 'FRA',
    'visibility': 'friends (2)',
    'distance_system': 'metric (0)',
    'weight_system': 'kilogram (0)',
    'temp_system': 'celsius (0)',
    'tz': 'Europe/Paris',
    'lang': None,
    'birthdate': '1991-09-05',
    'gender': 'male (0)',
    'objective': None,
    'verified': True,
    'avatar': 'avatar/abc.png',
    'polar_status': 'connected (1)',
    'withings_status': 'not_connected (0)',
    'garmin_status': 'need_reconnection (2)',
    'suunto_status': 'connected (1)',
    'quotas': {'exercises': {'current': 217, 'limit': 0}, 'groups': {'current': 4, 'limit': 10}},
}


def _rendered(renderer, *args, **kwargs):
    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=True, color_system=None)
    renderer(*args, console=console, **kwargs)
    return buf.getvalue()


@pytest.mark.parametrize(
    ('data', 'expected', 'absent'),
    [
        pytest.param(
            {'user': _WHOAMI_USER},
            ['julien@example.com', 'FRA', 'male', '✔ verified', 'friends', 'metric', 'Europe/Paris'],
            ['(2)', '(0)', 'avatar/abc.png'],
            id='full-card',
        ),
        pytest.param(
            {'user': _WHOAMI_USER},
            ['217 / ∞', '4 / 10'],
            [],
            id='quota-limits',
        ),
        pytest.param(
            {'user': _WHOAMI_USER},
            ['● polar', '○ withings', '● garmin', 'connected', 'not_connected', 'need_reconnection'],
            [],
            id='connection-states',
        ),
        pytest.param(
            {'user': {'email': 'jo@example.com', 'verified': False}},
            ['jo@example.com', '✗ unverified'],
            ['Preferences', 'Connections', 'Quotas'],
            id='missing-optionals-unverified',
        ),
        pytest.param(
            {'user': {**_WHOAMI_USER, 'streak': 7}},
            ['Other', 'streak', '7'],
            [],
            id='unknown-field-in-other-panel',
        ),
        pytest.param(
            {'id': 42, 'username': 'jo'},
            ['id', '42', 'jo'],
            [],
            id='fallback-shape',
        ),
    ],
)
def test_render_whoami(data, expected, absent):
    text = _rendered(render_whoami, data)
    for needle in expected:
        assert needle in text
    for needle in absent:
        assert needle not in text


@pytest.mark.parametrize(
    ('info', 'expected', 'absent'),
    [
        pytest.param(
            {'profile': 'default', 'base_url': 'https://api.x', 'logged_in': True, 'base_url_mismatch': False},
            ['default', '✔ logged in', 'https://api.x'],
            ['✗', '⚠', 'mismatch'],
            id='logged-in',
        ),
        pytest.param(
            {'profile': 'staging', 'base_url': 'https://api.x', 'logged_in': False, 'base_url_mismatch': True},
            ['staging', '✗ not logged in', '⚠ stored base_url differs'],
            ['✔'],
            id='logged-out-mismatch',
        ),
        pytest.param(
            {'profile': 'p', 'logged_in': True, 'access_token': 'tok-123'},
            ['access_token', 'tok-123'],
            [],
            id='show-token-row',
        ),
    ],
)
def test_render_auth_status(info, expected, absent):
    text = _rendered(render_auth_status, info)
    for needle in expected:
        assert needle in text
    for needle in absent:
        assert needle not in text


@pytest.mark.parametrize(
    ('active', 'profiles', 'expected'),
    [
        pytest.param('default', ['default', 'staging'], ['● default', '○ staging'], id='active-marked'),
        pytest.param('env-only', [], ['● env-only'], id='active-not-in-store'),
    ],
)
def test_render_profiles(active, profiles, expected):
    text = _rendered(render_profiles, active, profiles)
    for needle in expected:
        assert needle in text


def test_render_confirm():
    text = _rendered(render_confirm, 'token saved', 'profile default', 'https://api.x')
    assert '✔ token saved · profile default · https://api.x' in text


_OPERATION = {
    'method': 'POST',
    'path': '/v1/user/login',
    'operation_id': 'login_user',
    'tags': ['Auth endpoint'],
    'summary': 'Login User',
    'parameters': [
        {
            'name': 'obitrain',
            'in': 'cookie',
            'required': False,
            'schema': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
        }
    ],
    'request_body': {'application/json': {'$ref': '#/components/schemas/UserLoginReq'}},
    'responses': {
        '200': {'application/json': {'$ref': '#/components/schemas/UserGetResp'}},
        '422': {'application/json': {'$ref': '#/components/schemas/HTTPValidationError'}},
    },
    'schemas': {'UserLoginReq': {'type': 'object', 'properties': {'email': {'type': 'string'}}}},
}


@pytest.mark.parametrize(
    ('op', 'expected'),
    [
        pytest.param(
            _OPERATION,
            [
                'POST',
                '/v1/user/login',
                'Login User',
                'login_user · Auth endpoint',
                'obitrain',
                'cookie',
                'string | null',
                'UserLoginReq',
                '200',
                'UserGetResp',
                '422',
                'HTTPValidationError',
                '"email"',
            ],
            id='full-operation',
        ),
        pytest.param({'oops': True}, ['oops', 'true'], id='fallback-shape'),
    ],
)
def test_render_operation(op, expected):
    text = _rendered(render_operation, op)
    for needle in expected:
        assert needle in text


def test_render_pretty_records_join_scalar_lists(monkeypatch):
    monkeypatch.setattr('sys.stdout.isatty', lambda: True)
    for var in (
        'CLAUDECODE',
        'CLAUDE_CODE',
        'CURSOR_AGENT',
        'GITHUB_COPILOT',
        'AMAZON_Q',
        'OBI_AGENT_MODE',
        'NO_COLOR',
    ):
        monkeypatch.delenv(var, raising=False)
    out = io.StringIO()
    render([{'method': 'GET', 'path': '/v1/user', 'tags': ['Auth endpoint', 'User']}], 'pretty', stream=out)
    text = out.getvalue()
    assert 'Auth endpoint, User' in text
    assert '["Auth endpoint"' not in text


@pytest.mark.parametrize(
    ('env', 'value', 'expected'),
    [
        pytest.param('CLAUDECODE', '1', True, id='claudecode'),
        pytest.param('NO_COLOR', '1', True, id='no-color'),
        pytest.param('CURSOR_AGENT', '1', True, id='cursor'),
    ],
)
def test_agent_mode_from_env(monkeypatch, env, value, expected):
    for var in (
        'CLAUDECODE',
        'CLAUDE_CODE',
        'CURSOR_AGENT',
        'GITHUB_COPILOT',
        'AMAZON_Q',
        'OBI_AGENT_MODE',
        'NO_COLOR',
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv(env, value)
    assert agent_mode() is expected


def test_device_link_qr_renders_block_glyphs():
    qr = device_link_qr('obitrain://link-device?code=BCDF-2345')
    assert qr is not None
    # half-block glyphs only, deterministic for a given payload, no trailing blank line
    assert '█' in qr
    assert not qr.endswith('\n')
    assert qr == device_link_qr('obitrain://link-device?code=BCDF-2345')


def test_device_link_qr_distinct_per_code():
    assert device_link_qr('obitrain://link-device?code=AAAA-1111') != device_link_qr(
        'obitrain://link-device?code=BBBB-2222'
    )
