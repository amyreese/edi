# Copyright 2017 John Reese
# Licensed under the MIT license

from pathlib import Path
from typing import Any, Dict, List, Mapping

import toml
from attr import dataclass, fields


@dataclass
class Config:
    _tables: Dict[str, "Config"] = {}
    _content: Dict[str, Mapping[str, Any]] = {}

    def __getattr__(self, key: str) -> "Config":
        """
        Lazy load dataclasses from config tables as needed.

        This enables plugin-specific config values to be validated at runtime after
        the plugins have defined their config classes and only once they attempt to
        access those values.
        """
        key = key.lower()
        if key not in self._tables:
            subclasses = {c.__name__.lower(): c for c in Config.__subclasses__()}
            if key in subclasses:
                c = subclasses[key]
                content = self._content.get(key, {})
                tfields = [f.name for f in list(fields(c))]
                self._tables[key] = c(
                    **{k: v for k, v in content.items() if k in tfields}
                )
            else:
                raise AttributeError(f"config table {key} not found")
        return self._tables[key]

    @classmethod
    def load_from_file(cls, file_path: str) -> "Config":
        """Given a path to a local configuration file, read the config file and
        merge its contents onto the default configuration."""

        config = cls()
        path = Path(file_path).expanduser()
        if path.exists() and path.is_file():
            with open(path) as fd:
                contents = toml.load(fd)

            for key, value in contents.items():
                if isinstance(value, Mapping):
                    config._content[key.lower()] = value
                else:
                    raise KeyError(f"root-level config values not supported")

        else:
            raise RuntimeError(f"config path {path} not valid")

        return config


@dataclass
class bot(Config):
    token: str = "changeme"
    db_path: str = "edi.db"
    debug: bool = False
    log: str = ""
    uvloop: bool = True
    ignore_channels: List[str] = []


@dataclass
class units(Config):
    disable_units: List[str] = []
    disable_commands: List[str] = []
