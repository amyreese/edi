# Copyright 2016 John Reese
# Licensed under the MIT license

import logging

from ent import Ent

log = logging.getLogger(__name__)


class Message(Ent):
    """Base class for all Slack RTM messages."""
    pass


class Unit:
    ENABLED = True

    def __str__(self) -> str:
        return self.__class__.__name__

    @classmethod
    def all_units(cls, *, enabled_only=True):
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

    async def run(self) -> None:
        """The main entry point for units to run background tasks.

        This will only be called once by the main Edi framework, so any
        ongoing processing will require implementation of a run loop or
        dependence on another source of events.
        """
        log.debug("unit %s ready", self)

    async def stop(self) -> None:
        """Signal that any async work should be stopped.

        This will be called by the main Edi framework when the service needs
        to exit.  Units should keep track of """
        pass

    async def dispatch(self, message: Message) -> None:
        """Entry point for events received from the Slack RTM API.

        Any messages from the RTM API will be sent here, to be dispatched
        appropriately.  Default behavior is to look for a matching "on_event"
        method for the given message type, and will call that if found.
        """

        method = getattr(self, f"on_{message.type}", None)
        if method is not None:
            await method(message)
