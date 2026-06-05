from typing import Any

# Exit codes — chosen to avoid clashing with piou's 2 (argument errors).
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_AUTH = 4
EXIT_NETWORK = 5
EXIT_SERVER = 6
EXIT_CLIENT = 7


class ObiError(Exception):
    """Base error for the obi CLI; carries the process exit code to use."""

    exit_code: int = EXIT_USAGE


class AuthError(ObiError):
    """Authentication is required or failed."""

    exit_code = EXIT_AUTH

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class NetworkError(ObiError):
    """The request could not reach the server (connection, DNS, timeout)."""

    exit_code = EXIT_NETWORK


class ApiError(ObiError):
    """The API returned a non-2xx response during an auth/login flow."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        body: Any = None,
        request_id: str | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body
        self.request_id = request_id
        self.retry_after = retry_after

    @property
    def exit_code(self) -> int:  # type: ignore[override]
        return EXIT_SERVER if self.status >= 500 else EXIT_CLIENT
