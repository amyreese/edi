# Copyright 2017 John Reese
# Licensed under the MIT license

import websockets

from argparse import ArgumentParser
from os import path
from typing import List

from tasky import Tasky, Task

from .config import Config
from .log import Log, init_logger
from .slack import slacker


class Edi(Task):

    def __init__(self, config: Config) -> None:
        super().__init__()

        self.config = config
        self.slack = None
        self.conn = None

        Log.debug('Edi ready')

    async def connect(self) -> None:
        self.slack = slacker.Slacker(self.config.token)

        rtm_response = self.slack.rtm.start()
        if rtm_response.error:
            Log.error('Error requesting RTM connection: %s',
                      rtm_response.error)
            return False

        Log.info('Connecting to websocket URL %s', rtm_response.url)
        self.conn = await websockets.connect(rtm_response.url)
        Log.info(self.conn)

        return rtm_response

    async def run(self) -> None:
        response = await self.connect()

        if not response:
            Log.error('Connection failed, stopping Edi')
            return

        while self.running and not self.task.cancelled():
            try:
                msg = await self.conn.recv()
                Log.info(msg)

            except websockets.ConnectionClosed:
                Log.info('Connection closed')
                break

            except:
                Log.exception('Exception from RTM')
                break

        Log.info('Goodbye!')

    async def stop(self) -> None:
        if self.conn:
            Log.debug('closing RTM connection')
            await self.conn.close()

        await super().stop()


def init_from_config(config: Config) -> Edi:
    '''Initialize Edi from a loaded `Config` object.'''

    init_logger(stdout=True, file_path=config.log, debug=config.debug)
    Log.debug('logger initialized')

    tasky = Tasky()
    tasky.insert(Edi(config))
    return tasky.run_until_complete()


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
