from piou import Derived, Option

from obitrain.config import Config, resolve_config
from obitrain.output import OutputFormat

ProfileOpt = Option(None, '--profile', help='Credential profile to use (default: "default").')
BaseUrlOpt = Option(None, '--base-url', help='API base URL; overrides env and the stored value.')
TokenOpt = Option(None, '--token', help='Bearer API token to use without persisting it.')


def _resolve_output(
    # choices are derived from the OutputFormat Literal on the annotated parameter.
    output: OutputFormat | None = Option(None, '-o', '--output', help='Output format: pretty, json, raw or yaml.'),
    as_json: bool = Option(False, '--json', help='Shorthand for -o json.'),
) -> OutputFormat:
    """Default is pretty (plain JSON off-TTY / in agent environments); --json or -o force a format."""
    if output:
        return output
    return 'json' if as_json else 'pretty'


# Reusable Derived sentinel: any command can declare `output: OutputFormat = OutputOpt`.
OutputOpt = Derived(_resolve_output)


def make_config(
    profile: str | None = ProfileOpt,
    base_url: str | None = BaseUrlOpt,
    token: str | None = TokenOpt,
) -> Config:
    """Resolves the effective Config from the global --profile/--base-url/--token options and env."""
    return resolve_config(profile=profile, base_url=base_url, token=token)


# Reusable Derived sentinel: any command can declare `config: Config = ConfigArg`.
ConfigArg = Derived(make_config)
