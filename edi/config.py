# Copyright 2017 John Reese
# Licensed under the MIT license

import json

from attr import dataclass, fields_dict
from pathlib import Path
from typing import List


@dataclass
class Config:

    token: str = "changeme"
    db_path: str = "edi.db"
    debug: bool = False
    log: str = ""
    uvloop: bool = True

    disable_units: List = []
    disable_commands: List = ["tweet"]
    ignore_channels: List = []

    chatlog_root: str = "~/slacklogs"
    chatlog_format: str = "[{time}] {message}"

    twitter_consumer_key: str = ""
    twitter_consumer_secret: str = ""
    twitter_access_key: str = ""
    twitter_access_secret: str = ""
    twitter_timeline_channels: List = []

    @classmethod
    def load_defaults(cls) -> "Config":
        """Load the default configuration and return the object."""

        return cls()

    @classmethod
    def load_from_file(cls, file_path: str) -> "Config":
        """Given a path to a local configuration file, read the config file and
        merge its contents onto the default configuration."""

        kwargs = {}
        path = Path(file_path).expanduser()
        if path.exists() and path.is_file():
            with open(path) as fd:
                contents = json.load(fd)

            fields = fields_dict(Config)
            for name, field in fields.items():
                if name in contents and isinstance(contents[name], field.type):
                    kwargs[name] = contents[name]

        else:
            raise RuntimeError(f"config path {path} not valid")

        return cls(**kwargs)
