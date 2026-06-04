import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from piou import Option

from obitrain.client import ObiClient, read_response
from obitrain.config import Config
from obitrain.errors import EXIT_AUTH, EXIT_CLIENT, EXIT_OK, EXIT_SERVER, ObiError
from obitrain.options import ConfigArg, OutputOpt
from obitrain.output import OutputFormat, render, render_error


def api_cmd(
    path: str = Option(..., arg_name='path'),
    config: Config = ConfigArg,
    method: str | None = Option(None, '-X', '--method', help='HTTP method (default GET, or POST when -d is set).'),
    data: str | None = Option(None, '-d', '--data', help='Request body; @file or @- / - for stdin. Implies POST.'),
    query: list[str] = Option(None, '-q', '--query', help='Query params: k=v [k=v ...].'),
    header: list[str] = Option(None, '-H', '--header', help='Headers: k:v [k:v ...].'),
    output: OutputFormat = OutputOpt,
    dry_run: bool = Option(False, '-n', '--dry-run', help='Print the resolved request without sending it.'),
):
    """Make an authenticated request to any Obitrain API path (e.g. `obi api /v1/activities -q size=1`)."""
    from obitrain.runner import execute

    execute(_run(config, path, method, data, query or [], header or [], output, dry_run))


async def _run(
    config: Config,
    path: str,
    method: str | None,
    data: str | None,
    query: Sequence[str],
    header: Sequence[str],
    output: OutputFormat,
    dry_run: bool,
) -> int:
    params = _parse_pairs(query, '=', 'query')
    headers = _parse_headers(header)
    body, is_json = _read_body(data)
    resolved_method = (method or ('POST' if data is not None else 'GET')).upper()

    if dry_run:
        render(
            {
                'method': resolved_method,
                'url': _display_url(config.base_url, path),
                'query': params,
                'headers': _redact({**({'Authorization': 'Bearer …'} if config.creds.access_token else {}), **headers}),
                'body': body,
            },
            output,
        )
        return EXIT_OK

    async with ObiClient(config.base_url, config.creds) as client:
        resp = await client.request(
            resolved_method,
            _target(path),
            params=params or None,
            json_body=body if is_json else None,
            data=None if is_json else body,
            headers=headers or None,
        )
        status, payload, request_id = read_response(resp)
        retry_after = resp.headers.get('retry-after')

    _render_payload(payload, output)
    if status < 400:
        return EXIT_OK
    fields: dict[str, Any] = {'status': status, 'method': resolved_method, 'path': path, 'request_id': request_id}
    if status == 401:
        render_error('auth_required', detail='not authenticated; run `obi auth login`', **fields)
        return EXIT_AUTH
    render_error('http_error', retry_after=retry_after, **fields)
    return EXIT_SERVER if status >= 500 else EXIT_CLIENT


def _parse_pairs(items: Sequence[str], sep: str, kind: str) -> dict[str, str | list[str]]:
    out: dict[str, str | list[str]] = {}
    for item in items:
        key, found, value = item.partition(sep)
        if not found:
            raise ObiError(f'invalid {kind} {item!r}; expected key{sep}value')
        key, value = key.strip(), value.strip()
        if key in out:
            existing = out[key]
            out[key] = [*existing, value] if isinstance(existing, list) else [existing, value]
        else:
            out[key] = value
    return out


def _parse_headers(items: Sequence[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in items:
        key, found, value = item.partition(':')
        if not found:
            raise ObiError(f'invalid header {item!r}; expected key:value')
        headers[key.strip()] = value.strip()
    return headers


def _read_body(data: str | None) -> tuple[Any, bool]:
    """Returns (body, is_json): reads @file / stdin, parsing JSON when possible to set the content type."""
    if data is None:
        return None, False
    if data in ('-', '@-'):
        raw = sys.stdin.read()
    elif data.startswith('@'):
        raw = Path(data[1:]).read_text()
    else:
        raw = data
    try:
        return json.loads(raw), True
    except ValueError:
        return raw, False


def _target(path: str) -> str:
    if path.startswith(('http://', 'https://')):
        return path
    return path if path.startswith('/') else f'/{path}'


def _display_url(base_url: str, path: str) -> str:
    if path.startswith(('http://', 'https://')):
        return path
    return f'{base_url.rstrip("/")}{_target(path)}'


def _redact(headers: dict[str, str]) -> dict[str, str]:
    return {k: ('Bearer …' if k.lower() == 'authorization' else v) for k, v in headers.items()}


def _render_payload(payload: Any, output: OutputFormat) -> None:
    if output == 'raw' and not isinstance(payload, str):
        render(payload, 'json')
    else:
        render(payload, output)
