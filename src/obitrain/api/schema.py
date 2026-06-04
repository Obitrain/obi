import json
from functools import cache
from importlib.resources import files
from typing import Any

from piou import CommandGroup, Option

from obitrain.errors import ObiError
from obitrain.options import OutputOpt
from obitrain.output import OutputFormat, render
from obitrain.runner import guard

schema_group = CommandGroup('schema', help='Discover API operations and models from the bundled OpenAPI spec.')

_METHODS = ('get', 'post', 'put', 'patch', 'delete')


@cache
def _spec() -> dict[str, Any]:
    return json.loads((files('obitrain.api') / 'openapi.json').read_text())


def _operations() -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    for path, item in _spec()['paths'].items():
        for method, op in item.items():
            if method in _METHODS:
                ops.append(
                    {
                        'method': method.upper(),
                        'path': path,
                        'operation_id': op.get('operationId'),
                        'tags': op.get('tags', []),
                        'summary': op.get('summary'),
                    }
                )
    return ops


@schema_group.command('list', help='List API operations.')
def list_ops(
    output: OutputFormat = OutputOpt,
    tag: str | None = Option(None, '--tag', help='Only operations with this tag.'),
    grep: str | None = Option(None, '--grep', help='Filter by substring in path or operation id.'),
):
    ops = _operations()
    if tag:
        ops = [o for o in ops if tag in o['tags']]
    if grep:
        needle = grep.lower()
        ops = [o for o in ops if needle in o['path'].lower() or needle in (o['operation_id'] or '').lower()]
    render(ops, output)


@schema_group.command('tags', help='List tags with their operation counts.')
def list_tags(output: OutputFormat = OutputOpt):
    counts: dict[str, int] = {}
    for op in _operations():
        for tag in op['tags'] or ['<none>']:
            counts[tag] = counts.get(tag, 0) + 1
    render([{'tag': t, 'operations': n} for t, n in sorted(counts.items(), key=lambda kv: -kv[1])], output)


@schema_group.command('show', help='Show one operation: parameters, body, responses and referenced schemas.')
def show_op(
    ref: str = Option(..., arg_name='ref'),
    method: str | None = Option(None, '-X', '--method', help='Disambiguate when a path has several methods.'),
    output: OutputFormat = OutputOpt,
):
    with guard():
        op, path, verb = _find_operation(ref, method)
        render(
            {
                'method': verb.upper(),
                'path': path,
                'operation_id': op.get('operationId'),
                'tags': op.get('tags', []),
                'summary': op.get('summary'),
                'parameters': [
                    {
                        'name': p.get('name'),
                        'in': p.get('in'),
                        'required': p.get('required', False),
                        'schema': p.get('schema'),
                    }
                    for p in op.get('parameters', [])
                ],
                'request_body': _content_schemas(op.get('requestBody', {}).get('content', {})),
                'responses': {
                    code: _content_schemas(r.get('content', {})) for code, r in op.get('responses', {}).items()
                },
                'schemas': _schema_definitions(op),
            },
            output,
        )


def _find_operation(ref: str, method: str | None) -> tuple[dict[str, Any], str, str]:
    paths = _spec()['paths']
    path = ref if ref in paths else _match_template(ref)
    if path is not None:
        verbs = {m: op for m, op in paths[path].items() if m in _METHODS}
        if method:
            if method.lower() not in verbs:
                raise ObiError(f'no {method.upper()} on {path}')
            return verbs[method.lower()], path, method.lower()
        if len(verbs) != 1:
            raise ObiError(f'{path} has methods {sorted(v.upper() for v in verbs)}; pass -X to choose')
        ((verb, op),) = verbs.items()
        return op, path, verb
    for path, item in paths.items():
        for verb, op in item.items():
            if verb in _METHODS and op.get('operationId') == ref:
                return op, path, verb
    raise ObiError(f'no operation matching {ref!r}')


def _match_template(ref: str) -> str | None:
    """Match a concrete path like /v1/stats/activity/weekly against spec templates
    like /v1/stats/activity/{range_type}, preferring the match with most literal segments."""
    segments = ref.rstrip('/').split('/')
    best: tuple[int, str] | None = None
    for path in _spec()['paths']:
        parts = path.rstrip('/').split('/')
        if len(parts) != len(segments):
            continue
        literals = 0
        for part, segment in zip(parts, segments):
            if part.startswith('{') and part.endswith('}'):
                continue
            if part != segment:
                break
            literals += 1
        else:
            if best is None or literals > best[0]:
                best = (literals, path)
    return best[1] if best else None


def _content_schemas(content: dict[str, Any]) -> dict[str, Any]:
    return {media: spec.get('schema') for media, spec in content.items()}


def _schema_definitions(op: dict[str, Any]) -> dict[str, Any]:
    """Resolve the operation's referenced component schemas, transitively, to their definitions."""
    components = _spec().get('components', {}).get('schemas', {})
    pending = _referenced_schemas(op)
    resolved: dict[str, Any] = {}
    while pending:
        name = pending.pop()
        if name in resolved:
            continue
        definition = components.get(name)
        if definition is None:
            continue
        resolved[name] = definition
        pending |= _referenced_schemas(definition) - resolved.keys()
    return dict(sorted(resolved.items()))


def _referenced_schemas(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == '$ref' and isinstance(value, str):
                found.add(value.rsplit('/', 1)[-1])
            else:
                found |= _referenced_schemas(value)
    elif isinstance(node, list):
        for item in node:
            found |= _referenced_schemas(item)
    return found
