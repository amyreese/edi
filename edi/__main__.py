# Copyright 2017 John Reese
# Licensed under the MIT license

import click

from .bot import init_from_config
from .config import Config


@click.command("edi")
@click.option("--debug", "-D", is_flag=True, help="enable debug/verbose output")
@click.option(
    "--config",
    default="config.yaml",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="path to configuration file",
)
@click.option(
    "--log",
    default=None,
    type=click.Path(exists=False, resolve_path=True, dir_okay=False, writable=True),
    help="path to log program output",
)
@click.option("--version", "-V", is_flag=True, help="show version and exit")
def init_from_cli(
    debug: bool = False, config: str = "", log: str = "", version: bool = False
) -> None:
    """Simple Slack Bot"""

    if version:
        from edi import __version__

        print(f"edi v{__version__}")
        return

    if config is not None:
        config = Config.load_from_file(config)
    else:
        config = Config.load_defaults()

    if log is not None:
        config.log = log

    if debug:
        config.debug = True

    init_from_config(config)


if __name__ == "__main__":
    init_from_cli()
