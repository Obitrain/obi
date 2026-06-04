from piou import Derived, Option

from obitrain.config import Config, resolve_config

ProfileOpt = Option(None, '--profile', help='Credential profile to use (default: "default").')
BaseUrlOpt = Option(None, '--base-url', help='API base URL; overrides env and the stored value.')
TokenOpt = Option(None, '--token', help='Bearer access token to use (ephemeral; disables refresh).')
# choices are derived from the OutputFormat Literal on the annotated parameter.
OutputOpt = Option('json', '-o', '--output', help='Output format: json, pretty, raw or yaml.')


def make_config(
    profile: str | None = ProfileOpt,
    base_url: str | None = BaseUrlOpt,
    token: str | None = TokenOpt,
) -> Config:
    """Resolves the effective Config from the global --profile/--base-url/--token options and env."""
    return resolve_config(profile=profile, base_url=base_url, token=token)


# Reusable Derived sentinel: any command can declare `config: Config = ConfigArg`.
ConfigArg = Derived(make_config)
