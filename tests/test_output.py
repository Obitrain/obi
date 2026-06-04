import io
import json

import pytest
import yaml

from obitrain.output import agent_mode, render, render_error


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
