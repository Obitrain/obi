import json
import os
import sys
from typing import Any, Literal, TextIO

import yaml
from rich import box
from rich.console import Console
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
            table.add_row(*(_cell(item.get(column)) for column in columns))
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
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render_error(error: str, **fields: Any) -> None:
    """Writes a one-line diagnostic JSON object to stderr for agents to parse."""
    payload = {'error': error, **{k: v for k, v in fields.items() if v is not None}}
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
