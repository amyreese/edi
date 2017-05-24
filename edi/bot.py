# Copyright 2017 John Reese
# Licensed under the MIT license

import asyncio
import signal

try:
    import uvloop
except ImportError:
    uvloop = None

from argparse import ArgumentParser
from os import path
from typing import List

from .config import Config
from .log import Log, init_logger


class Edi:
    """Main event framework for the bot."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.slack = None
        self.conn = None
        self.loop = None

        Log.debug('Edi ready')

    def start(self) -> None:
        """Start the asyncio event loop, and close it when we're done."""
        if uvloop and self.config.uvloop:
            Log.debug('Using uvloop')
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        self.loop = asyncio.new_event_loop()

        if self.config.debug:
            self.loop.set_debug(True)

        self.loop.add_signal_handler(signal.SIGINT, self.sigterm)
        self.loop.add_signal_handler(signal.SIGTERM, self.sigterm)

        asyncio.ensure_future(self.run(), loop=self.loop)
        self.loop.run_forever()
        self.loop.close()

    def sigterm(self) -> None:
        """Handle Ctrl-C or SIGTERM by stopping the event loop nicely."""
        Log.warning('Signal received, stopping execution')
        asyncio.ensure_future(self.stop(), loop=self.loop)

    async def run(self) -> None:
        """Execute all the bits of Edi."""
        Log.info('Hello!')
        Log.info('Goodbye!')

    async def stop(self) -> None:
        """Stop all the bits of Edi."""
        self.loop.stop()


def init_from_config(config: Config) -> Edi:
    '''Initialize Edi from a loaded `Config` object.'''

    init_logger(stdout=True, file_path=config.log, debug=config.debug)
    Log.debug('logger initialized')

    return Edi(config).start()


def init_from_cli(argv: List[str]=None) -> Edi:
    '''Initialize Edi from the CLI, using sys.argv (default) or an optional
    list of arguments.'''

    options = parse_args(argv)
    config = Config.load_from_file(options.config)

    if options.log:
        config.log = options.log

    if options.debug:
        config.debug = options.debug

    return init_from_config(config)


def parse_args(argv: List[str]=None) -> object:
    '''Parse and perform basic validation of CLI options.'''

    parser = ArgumentParser(description='simple Slack bot')
    parser.add_argument('-D', '--debug', action='store_true', default=False,
                        help='enable debug/verbose output')
    parser.add_argument('--config', type=str, default='config.yaml',
                        metavar='PATH',
                        help='path to configuration file if not in cwd')
    parser.add_argument('--log', type=str, default=None, metavar='PATH',
                        help='path to log program output')

    options = parser.parse_args(argv)

    if path.isdir(options.config):
        options.config = path.join(options.config, 'config.yaml')

    if not path.isfile(options.config):
        parser.error('config path "%s" does not exist' % (options.config,))

    if options.log:
        try:
            with open(options.log, 'a'):
                pass
        except:
            parser.error('log path "%s" invalid' % (options.log,))

    return options
