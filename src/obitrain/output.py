import json
import os
import sys
from typing import Any, Literal, TextIO

import yaml
from rich.console import Console

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
        Console(file=stream).print_json(data=value)
        return
    print(json.dumps(value, indent=2, ensure_ascii=False), file=stream)


def render_error(error: str, **fields: Any) -> None:
    """Writes a one-line diagnostic JSON object to stderr for agents to parse."""
    payload = {'error': error, **{k: v for k, v in fields.items() if v is not None}}
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
