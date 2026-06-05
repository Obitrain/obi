# DESCRIPTION: Regenerate docs/assets/images/whoami.svg, the `obi auth whoami` card shown on the docs landing page.
# USAGE: uv run python bin/gen-whoami-svg.py

from pathlib import Path

from rich.console import Console

from obitrain.api.schema import annotate_enums
from obitrain.output import render_whoami

PAYLOAD = {
    'user': {
        'email': 'ada@example.com',
        'username': 'ada',
        'country': 'FRA',
        'visibility': 2,
        'distance_system': 0,
        'weight_system': 0,
        'temp_system': 0,
        'tz': 'Europe/Paris',
        'lang': 'fr',
        'birthdate': '1990-12-10',
        'gender': 1,
        'objective': 2,
        'verified': True,
        'avatar': None,
        'polar_status': 1,
        'withings_status': 0,
        'garmin_status': 1,
        'suunto_status': 0,
        'quotas': {'exercises': {'current': 42, 'limit': 200}, 'groups': {'current': 3, 'limit': 10}},
    }
}

console = Console(record=True, width=72)
render_whoami(annotate_enums(PAYLOAD, 'GET', '/v1/user'), console=console)
out = Path(__file__).parent.parent / 'docs' / 'assets' / 'images' / 'whoami.svg'
out.write_text(console.export_svg(title='obi auth whoami'))
print(f'wrote {out}')
