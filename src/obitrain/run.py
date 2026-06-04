from piou import Cli
from piou.formatter import RichFormatter

from obitrain import __version__
from obitrain.api import api_cmd
from obitrain.api.schema import schema_group
from obitrain.auth import auth_group

cli = Cli(
    description='Public, agent-first CLI for the Obitrain API.',
    formatter=RichFormatter(show_default=True),
    show_help_on_error=True,
)

cli.add_command('api', api_cmd, help='Make an authenticated request to any API path.')
cli.add_command_group(auth_group)
cli.add_command_group(schema_group)


@cli.command('version', help='Show the obi version.')
def _version() -> None:
    print(__version__)


def run() -> None:
    cli.run()
