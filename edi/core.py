# Copyright 2016 John Reese
# Licensed under the MIT license

import inspect
import logging
import re
from types import FunctionType
from typing import Any, Callable, Dict, Pattern, Set, Tuple, Type, TypeVar

from aioslack import Event, Slack

log = logging.getLogger(__name__)

COMMANDS: Dict[str, Tuple[Any, Pattern, str]] = {}
T = TypeVar("T", bound=FunctionType)


def command(
    args: str = r"(.*)", name: str = "", description: str = ""
) -> Callable[[T], T]:
    """Decorator for automating command/args declaration and dispatch."""

    def wrapper(fn: T) -> T:
        if fn.__name__ == fn.__qualname__:
            # TODO: maybe handle raw functions
            raise ValueError("@command takes class methods only")

        cmd = name.lower() if name else fn.__name__.lower()
        if cmd in COMMANDS:
            unit, _regex, _description = COMMANDS[name]
            raise ValueError(f'command "{cmd}" already claimed by {unit.__name__}')

        module = inspect.getmodule(fn)
        cls_name = fn.__qualname__.split(".")[0]
        fn_name = fn.__name__

        COMMANDS[cmd] = ((module, cls_name, fn_name), re.compile(args), description)

        return fn

    return wrapper


def materialize_commands(units: Dict[Type["Unit"], "Unit"]) -> None:
    for name in list(COMMANDS):
        info, args, description = COMMANDS[name]
        try:
            module, cls_name, fn_name = info
            cls = getattr(module, cls_name)
            method = None
            instance = units[cls]
            method = getattr(instance, fn_name)
            if method:
                COMMANDS[name] = method, args, description
            else:
                raise AttributeError(f"no active unit of {cls} with method {fn_name}")

        except (AttributeError, KeyError):
            COMMANDS.pop(name)


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

    async def dispatch(self, event: Event) -> None:
        """
        Entry point for events received from the Slack RTM API.

        Any messages from the RTM API will be sent here, to be dispatched
        appropriately.  Default behavior is to look for a matching "on_event"
        method for the given message type, and will call that if found.
        """

        method = getattr(self, f"on_{event.type}", self.on_default)
        await method(event)

    async def on_default(self, event: Event) -> None:
        """Default message handler when specific handlers aren't defined."""
        pass
