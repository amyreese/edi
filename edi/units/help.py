# Copyright 2017 John Reese
# Licensed under the MIT license

import logging
import random

from aioslack import Channel, User

from edi import Unit, command
from edi.core import COMMANDS

log = logging.getLogger(__name__)


@command("help", description="[command]: show command details")
@command("hello", description=": <insert witty help text here>")
class Help(Unit):

    async def help(self, channel: Channel, user: User, phrase: str) -> str:
        phrase = phrase.strip().lower()
        detail = bool(phrase)
        if not phrase:
            command_list = list(COMMANDS.keys())
        else:
            names = phrase.split()
            command_list = [c for c in COMMANDS if c in names]
            if not command_list:
                return "No matching commands"

        helps = []
        for name in sorted(command_list):
            _unit, args, description = COMMANDS[name]
            if detail:
                description = "\n".join(
                    f"    {line.strip()}" for line in description.splitlines()
                )
                helps.extend(
                    [
                        f"{name}:",
                        f"{description}",
                        f"    argument regex: {args.pattern}",
                    ]
                )
            else:
                description = description.splitlines()[0].strip()
                helps.append(f"{name} {description}")

        text = "\n".join(helps)
        text = f"```\n{text}\n```"

        if len(text) > 1000:
            # todo: IM user with full list of commands
            return ""

        return text

    async def hello(self, channel: Channel, user: User, phrase: str) -> str:
        # http://masseffect.wikia.com/wiki/Legion/Unique_dialogue
        humor = [
            "These facilities are inadequate.",
            "Metal detectors are inconvenient.",
            "Tactical disadvantage. Recommend orbital fire support.",
            "This platform is not available for experimentation.",
            "Your operating system is unstable. You will fail.",
            "The first thing a god masters is itself.",
            "Our analysis of organic humour suggests an 87.3% chance "
            'that you expect us to respond with, "You are only human."',
        ]
        return random.choice(humor)
