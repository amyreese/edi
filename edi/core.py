# Copyright 2016 John Reese
# Licensed under the MIT license

import logging

from attr import dataclass
from typing import Set, Type

from aioslack import Slack

log = logging.getLogger(__name__)


@dataclass
class Message:
    """Base class for all Slack RTM messages."""

    type: str


class Unit:
    ENABLED = True

    def __init__(self, slack: Slack) -> None:
        self.slack = slack

    def __str__(self) -> str:
        return self.__class__.__name__

    @classmethod
    def all_units(cls, *, enabled_only: bool = True) -> Set[Type["Unit"]]:
        """Return all defined subclasses of Unit, recursively."""
        seen = set()
        queue = set([cls])

        while queue:
            c = queue.pop()
            seen.add(c)

            sc = c.__subclasses__()
            for c in sc:
                if c not in seen:
                    queue.add(c)

        seen.remove(cls)  # exclude the base class

        if enabled_only:
            seen = {c for c in seen if c.ENABLED}

        return seen

    async def start(self) -> None:
        """
        The main entry point for units to run background tasks.

        This will only be called once by the main Edi framework, so any
        ongoing processing will require implementation of a run loop or
        dependence on another source of events.
        """
        log.debug("unit %s ready", self)

    async def stop(self) -> None:
        """
        Signal that any async work should be stopped.

        This will be called by the main Edi framework when the service needs
        to exit.  Units should keep track of any async tasks currently pending
        and cancel them here.  Edi assumes this unit is completely stopped
        once this coroutine is completed."""
        pass

    async def dispatch(self, message: Message) -> None:
        """
        Entry point for events received from the Slack RTM API.

        Any messages from the RTM API will be sent here, to be dispatched
        appropriately.  Default behavior is to look for a matching "on_event"
        method for the given message type, and will call that if found.
        """

        method = getattr(self, f"on_{message.type}", self.on_default)
        await method(message)

    async def on_default(self, message: Message) -> None:
        """Default message handler when specific handlers aren't defined."""
        pass
