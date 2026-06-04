import asyncio
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
from typing import Any

import niquests

from obitrain.errors import EXIT_NETWORK, ApiError, AuthError, ObiError
from obitrain.output import render_error


@contextmanager
def guard() -> Iterator[None]:
    """Wraps a synchronous command body, mapping an ObiError to a stderr JSON diagnostic + exit code."""
    try:
        yield
    except ObiError as exc:
        render_error('error', detail=str(exc))
        raise SystemExit(exc.exit_code) from exc


def execute(coro: Coroutine[Any, Any, int]) -> None:
    """Runs an async command body returning an exit code, mapping errors to exit codes + stderr JSON.

    Command coroutines return their process exit code (0 on success). Raised obi/niquests errors are
    turned into a one-line diagnostic JSON on stderr and the matching exit code, so agents get a
    deterministic signal without parsing prose.
    """
    try:
        code = asyncio.run(coro)
    except AuthError as exc:
        render_error('auth_required', detail=str(exc), status=exc.status)
        code = exc.exit_code
    except ApiError as exc:
        render_error(
            'http_error',
            status=exc.status,
            detail=str(exc),
            request_id=exc.request_id,
            retry_after=exc.retry_after,
        )
        code = exc.exit_code
    except (niquests.exceptions.ConnectionError, niquests.exceptions.Timeout) as exc:
        render_error('network', detail=str(exc))
        code = EXIT_NETWORK
    except ObiError as exc:
        render_error('error', detail=str(exc))
        code = exc.exit_code
    if code:
        raise SystemExit(code)
