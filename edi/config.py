# Copyright 2017 John Reese
# Licensed under the MIT license

from ent import Ent, yaml
from os import path


class Config(Ent):

    @classmethod
    def load_defaults(cls) -> "Config":
        """Load the default configuration and return the object."""

        cwd = path.abspath(path.dirname(__file__))
        defaults_path = path.join(cwd, "defaults.yaml")

        with open(defaults_path) as fd:
            contents = yaml.safe_load(fd)
            return Config.load(contents)

    @classmethod
    def load_from_file(cls, file_path) -> "Config":
        """Given a path to a local configuration file, read the config file and
        merge its contents onto the default configuration."""

        defaults = cls.load_defaults()

        with open(file_path) as fd:
            contents = yaml.safe_load(fd)
            overrides = Config.load(contents)

            return Config.merge(defaults, overrides)
