from importlib.metadata import version

__version__ = version('obitrain')

from obitrain.run import run

__all__ = ('run', '__version__')
