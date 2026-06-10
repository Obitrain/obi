import io
import json
import os
import re
import sys
from typing import Any, Literal, TextIO

import yaml
from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

OutputFormat = Literal['json', 'pretty', 'raw', 'yaml']

_AGENT_ENV = ('CLAUDECODE', 'CLAUDE_CODE', 'CURSOR_AGENT', 'GITHUB_COPILOT', 'AMAZON_Q', 'OBI_AGENT_MODE')


def agent_mode() -> bool:
    """True when output should be machine-friendly: an agent env var, NO_COLOR, or a non-TTY stdout."""
    if any(os.environ.get(v) for v in _AGENT_ENV):
        return True
    if os.environ.get('NO_COLOR'):
        return True
    return not sys.stdout.isatty()


def render(value: Any, fmt: OutputFormat = 'json', *, stream: TextIO | None = None) -> None:
    """Renders a value to `stream` in the requested format; json is the agent-friendly default."""
    stream = stream or sys.stdout
    if fmt == 'raw':
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        print(text, file=stream)
        return
    if fmt == 'yaml':
        yaml.safe_dump(value, stream, sort_keys=False, allow_unicode=True)
        return
    if fmt == 'pretty' and not agent_mode():
        _render_pretty(value, Console(file=stream))
        return
    print(json.dumps(value, indent=2, ensure_ascii=False), file=stream)


_MAX_TABLE_COLUMNS = 8


def _render_pretty(value: Any, console: Console) -> None:
    """Tables for records and objects (nested keys dotted); highlighted JSON as the fallback."""
    if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        columns: list[str] = []
        for item in value:
            columns.extend(k for k in item if k not in columns)
        if len(columns) > _MAX_TABLE_COLUMNS:  # wide records read better as one block each
            for index, item in enumerate(value):
                console.print(_kv_table(item, title=f'#{index + 1}'))
            return
        table = Table(box=box.SIMPLE_HEAD, header_style='bold cyan')
        for column in columns:
            table.add_column(column, overflow='fold')
        for item in value:
            table.add_row(*(_record_cell(column, item.get(column)) for column in columns))
        console.print(table)
    elif isinstance(value, dict):
        console.print(_kv_table(value))
    else:
        console.print_json(data=value)


def _kv_table(value: dict[str, Any], title: str | None = None) -> Table:
    table = Table(show_header=False, box=box.SIMPLE, pad_edge=False, title=title, title_justify='left')
    table.add_column(style='bold cyan')
    table.add_column(overflow='fold')
    for key, item in _flatten(value):
        table.add_row(key, _cell(item))
    return table


def _flatten(value: dict[str, Any], prefix: str = ''):
    for key, item in value.items():
        if isinstance(item, dict) and item:
            yield from _flatten(item, f'{prefix}{key}.')
        else:
            yield f'{prefix}{key}', item


def _cell(value: Any) -> str:
    if value is None:
        return '[dim]null[/dim]'
    if value is True:
        return '[italic green3]true[/italic green3]'
    if value is False:
        return '[italic red3]false[/italic red3]'
    if isinstance(value, list) and value and not any(isinstance(item, (dict, list)) for item in value):
        return ', '.join(_cell(item) for item in value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


_METHOD_STYLES = {'GET': 'cyan', 'POST': 'green3', 'PUT': 'yellow3', 'PATCH': 'yellow3', 'DELETE': 'red3'}


def _record_cell(column: str, value: Any) -> str:
    if column == 'method' and isinstance(value, str) and (style := _METHOD_STYLES.get(value.upper())):
        return f'[bold {style}]{value}[/bold {style}]'
    return _cell(value)


_PREF_FIELDS = ('visibility', 'distance_system', 'weight_system', 'temp_system', 'tz', 'lang', 'objective')
_IDENTITY_FIELDS = ('email', 'username', 'country', 'gender', 'birthdate', 'verified')
_STATUS_DOTS = {'connected': '[green3]●[/green3]', 'need_reconnection': '[yellow3]●[/yellow3]'}


def render_whoami(data: Any, *, console: Console | None = None) -> None:
    """Renders an enum-annotated whoami payload as a profile card: identity header, preferences and
    third-party connections side by side, quotas. Falls back to the generic pretty renderer when the
    payload is not the expected `{'user': {...}}` shape; unknown user fields land in an Other panel."""
    console = console or Console()
    user = data.get('user') if isinstance(data, dict) else None
    if not isinstance(user, dict):
        _render_pretty(data, console)
        return
    console.print(_identity_panel(user))
    middle = [panel for panel in (_prefs_panel(user), _connections_panel(user)) if panel is not None]
    if middle:
        console.print(Columns(middle))
    if isinstance(quotas := user.get('quotas'), dict) and quotas:
        console.print(_quotas_panel(quotas))
    known = {*_IDENTITY_FIELDS, *_PREF_FIELDS, 'quotas', 'avatar'}
    leftover = {k: v for k, v in user.items() if k not in known and not k.endswith('_status')}
    if leftover:
        console.print(_panel(_kv_table(leftover), title='Other'))


def _panel(body: Any, title: str | None = None) -> Panel:
    return Panel(body, title=title and f'[bold cyan]{title}[/bold cyan]', title_align='left', border_style='dim')


def _panel_table(rows: list[tuple[str, str]]) -> Table:
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style='bold cyan')
    table.add_column(overflow='fold')
    for key, value in rows:
        table.add_row(key, value)
    return table


def _label(value: Any) -> str:
    """Bare label of an `annotate_enums`-style 'name (value)' string; generic cell text otherwise."""
    if isinstance(value, str):
        return re.sub(r' \(\d+\)$', '', value)
    return _cell(value)


def _identity_panel(user: dict[str, Any]) -> Panel:
    lines = []
    if email := user.get('email'):
        lines.append(f'[bold]{email}[/bold]')
    meta = [_label(user[k]) for k in ('country', 'gender', 'birthdate') if user.get(k) is not None]
    if (verified := user.get('verified')) is not None:
        meta.append('[green3]✔ verified[/green3]' if verified else '[red3]✗ unverified[/red3]')
    if meta:
        lines.append('[dim] · [/dim]'.join(meta))
    return _panel('\n'.join(lines), title=user.get('username'))


def _prefs_panel(user: dict[str, Any]) -> Panel | None:
    rows = [(key.removesuffix('_system'), _label(user[key])) for key in _PREF_FIELDS if user.get(key) is not None]
    return _panel(_panel_table(rows), title='Preferences') if rows else None


def _connections_panel(user: dict[str, Any]) -> Panel | None:
    rows = []
    for key, value in user.items():
        if not key.endswith('_status'):
            continue
        label = _label(value)
        dot = _STATUS_DOTS.get(label, '[dim]○[/dim]')
        rows.append((f'{dot} {key.removesuffix("_status")}', label if label == 'connected' else f'[dim]{label}[/dim]'))
    return _panel(_panel_table(rows), title='Connections') if rows else None


def _quotas_panel(quotas: dict[str, Any]) -> Panel:
    rows = []
    for name, quota in quotas.items():
        if isinstance(quota, dict) and 'current' in quota:
            limit = quota.get('limit')
            rows.append((name, f'{quota["current"]} / {"∞" if not limit else limit}'))
        else:
            rows.append((name, _cell(quota)))
    return _panel(_panel_table(rows), title='Quotas')


def device_link_qr(url: str) -> str | None:
    """Renders `url` as a terminal-scannable QR built from unicode half-blocks, or None if `qrcode`
    is unavailable. `invert=True` yields dark modules on a light frame, the readable polarity on the
    dark terminals most developers run."""
    try:
        import qrcode
    except ImportError:
        return None
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make()
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue().rstrip('\n')


def render_confirm(status: str, *details: str, console: Console | None = None) -> None:
    """Prints a one-line green-check confirmation, details dim and dot-separated."""
    console = console or Console()
    parts = [f'[green3]✔[/green3] {status}', *(f'[dim]{d}[/dim]' for d in details)]
    console.print(' [dim]·[/dim] '.join(parts))


def render_auth_status(info: dict[str, Any], *, console: Console | None = None) -> None:
    """Renders the `auth status` payload as a card: logged-in marker, settings rows, and the
    base_url mismatch flag as an explicit warning line."""
    console = console or Console()
    logged_in = info.get('logged_in')
    body: list[Any] = ['[green3]✔ logged in[/green3]' if logged_in else '[red3]✗ not logged in[/red3]']
    rows = [(k, _cell(v)) for k, v in info.items() if k not in ('profile', 'logged_in', 'base_url_mismatch')]
    if rows:
        body.append(_panel_table(rows))
    if info.get('base_url_mismatch'):
        body.append('[yellow3]⚠ stored base_url differs from the configured one[/yellow3]')
    console.print(_panel(Group(*body), title=info.get('profile')))


def render_profiles(active: str, profiles: list[str], *, console: Console | None = None) -> None:
    """Lists credential profiles with a marker on the active one."""
    console = console or Console()
    names = profiles if active in profiles else [active, *profiles]
    for name in names:
        if name == active:
            console.print(f'[green3]●[/green3] [bold]{name}[/bold]')
        else:
            console.print(f'[dim]○[/dim] {name}')


def render_operation(op: Any, *, console: Console | None = None) -> None:
    """Renders a `schema show` payload as cards: method/path header, parameters, request body,
    responses, and referenced schemas as highlighted JSON. Falls back to the generic renderer
    when the payload is not the expected operation shape."""
    console = console or Console()
    if not isinstance(op, dict) or 'method' not in op or 'path' not in op:
        _render_pretty(op, console)
        return
    console.print(_operation_header(op))
    if params := op.get('parameters'):
        table = Table(box=box.SIMPLE_HEAD, header_style='bold cyan')
        for column in ('name', 'in', 'required', 'type'):
            table.add_column(column, overflow='fold')
        for p in params:
            table.add_row(p.get('name'), p.get('in'), _cell(p.get('required', False)), _schema_ref(p.get('schema')))
        console.print(_panel(table, title='Parameters'))
    if body := op.get('request_body'):
        rows = [(media, _schema_ref(schema)) for media, schema in body.items()]
        console.print(_panel(_panel_table(rows), title='Request body'))
    if responses := op.get('responses'):
        rows = []
        for code, content in responses.items():
            style = 'green3' if str(code).startswith('2') else 'cyan' if str(code).startswith('3') else 'red3'
            refs = ', '.join(_schema_ref(schema) for schema in content.values()) if content else '[dim]—[/dim]'
            rows.append((f'[{style}]{code}[/{style}]', refs))
        console.print(_panel(_panel_table(rows), title='Responses'))
    for name, definition in (op.get('schemas') or {}).items():
        console.print(_panel(JSON(json.dumps(definition, ensure_ascii=False)), title=name))


def _operation_header(op: dict[str, Any]) -> Panel:
    method = str(op['method']).upper()
    style = _METHOD_STYLES.get(method, 'cyan')
    lines = []
    if summary := op.get('summary'):
        lines.append(f'[bold]{summary}[/bold]')
    meta = [str(part) for part in (op.get('operation_id'), *(op.get('tags') or [])) if part]
    if meta:
        lines.append(f'[dim]{" · ".join(meta)}[/dim]')
    return _panel('\n'.join(lines), title=f'[bold {style}]{method}[/bold {style}] {op["path"]}')


def _schema_ref(schema: Any) -> str:
    """Short human name for an OpenAPI schema node: ref name, scalar type, unions and arrays."""
    if not isinstance(schema, dict):
        return _cell(schema)
    if '$ref' in schema:
        return str(schema['$ref']).rsplit('/', 1)[-1]
    if 'anyOf' in schema:
        return ' | '.join(_schema_ref(s) for s in schema['anyOf'])
    if schema.get('type') == 'array':
        return f'{_schema_ref(schema.get("items", {}))}[]'
    return str(schema.get('type') or json.dumps(schema, ensure_ascii=False))


def render_error(error: str, **fields: Any) -> None:
    """Writes a one-line diagnostic JSON object to stderr for agents to parse."""
    payload = {'error': error, **{k: v for k, v in fields.items() if v is not None}}
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
