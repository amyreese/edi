# Copyright 2016 John Reese
# Licensed under the MIT license

from argparse import ArgumentParser
from os import path

from .config import Config
from .log import Log, init_logger


class Edi(object):
    def __init__(self, config):
        self.config = config
        self.slack = None

        Log.debug('Edi ready')

    @property
    def connected(self):
        return self.slack is not None

    def start(self):
        Log.info('starting event loop')
        pass


def init_from_config(config):
    '''Initialize Edi from a loaded `Config` object.'''

    init_logger(stdout=True, file_path=config.log, debug=config.debug)
    Log.debug('logger initialized')

    return Edi(config)


def init_from_cli(argv=None):
    '''Initialize Edi from the CLI, using sys.argv (default) or an optional
    list of arguments.'''

    options = parse_args(argv)
    config = Config.load_from_file(options.config)

    if options.log:
        config.log = options.log

    if options.debug:
        config.debug = options.debug

    return init_from_config(config)


def parse_args(argv=None):
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
