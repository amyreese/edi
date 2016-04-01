# Copyright 2016 John Reese
# Licensed under the MIT license

import asyncio
import signal
import websockets

from argparse import ArgumentParser
from os import path
from typing import List

from .common import Task, PeriodicTask
from .config import Config
from .log import Log, init_logger


class SecondLoop(PeriodicTask):
    INTERVAL = 5.0

    async def run(self):
        Log.info('second loop running')


class Edi(Task):

    def __init__(self, config: Config) -> None:
        self.config = config
        self.slack = None
        self.loop = None
        self.running = True
        self.stop_attempts = 0

        Log.debug('Edi ready')

    @property
    def connected(self) -> bool:
        return self.slack is not None

    async def run(self) -> None:
        Log.info('in main loop')
        async with websockets.connect('ws://localhost:2345') as conn:
            self.slack = conn
            Log.info('connected')

            SecondLoop.start()

            counter = 0
            while self.running and counter <= 3:
                Log.info('sending %s', counter)
                await conn.send(str(counter))
                retval = await conn.recv()
                Log.info('received %s', retval)
                await asyncio.sleep(1.0)
                counter += 1

        self.slack = None
        Log.info('main loop completed')

    def ctrlc(self) -> None:
        if self.connected and self.stop_attempts < 1:
            Log.info('stopping main loop')
            self.running = False
            self.stop_attempts += 1
        else:
            Log.info('force stopping event loop')
            self.loop.stop()

    def start(self) -> None:
        Log.info('starting event loop')

        self.loop = asyncio.get_event_loop()
        self.loop.add_signal_handler(signal.SIGINT, self.ctrlc)
        self.loop.run_until_complete(self.start_task())
        self.loop.run_until_complete(Task.stop_all())

        Log.info('event loop stopped')


def init_from_config(config: Config) -> Edi:
    '''Initialize Edi from a loaded `Config` object.'''

    init_logger(stdout=True, file_path=config.log, debug=config.debug)
    Log.debug('logger initialized')

    return Edi(config)


def init_from_cli(argv: List[str] = None) -> Edi:
    '''Initialize Edi from the CLI, using sys.argv (default) or an optional
    list of arguments.'''

    options = parse_args(argv)
    config = Config.load_from_file(options.config)

    if options.log:
        config.log = options.log

    if options.debug:
        config.debug = options.debug

    return init_from_config(config)


def parse_args(argv: List[str] = None) -> object:
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
