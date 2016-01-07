# Copyright 2016 John Reese
# Licensed under the MIT license

import logging
import sys

from logging import Formatter, StreamHandler, FileHandler

Log = logging.getLogger('edi')


def init_logger(stdout=True, file_path=None, debug=False):
    '''Initialize the logging system for stdout and an optional log file.'''

    level = logging.DEBUG if debug else logging.INFO
    Log.setLevel(level)

    logging.addLevelName(logging.ERROR, 'E')
    logging.addLevelName(logging.WARNING, 'W')
    logging.addLevelName(logging.INFO, 'I')
    logging.addLevelName(logging.DEBUG, 'V')

    stdout_fmt = Formatter('%(levelname)s: %(message)s')
    verbose_fmt = Formatter('%(asctime)s  %(levelname)s  '
                            '%(module)s:%(funcName)s  %(message)s')

    if stdout:
        handler = StreamHandler(sys.stdout)
        handler.setLevel(level)

        if debug:
            handler.setFormatter(verbose_fmt)
        else:
            handler.setFormatter(stdout_fmt)

        Log.addHandler(handler)

    if file_path:
        handler = FileHandler(file_path)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(verbose_fmt)

        Log.addHandler(handler)

    return Log
