# Copyright 2017 John Reese
# Licensed under the MIT license

import asyncio
import logging
import re
import signal
from typing import Dict, Optional, Type

from ent import Singleton

from aioslack import Event, Slack, SlackError

from .config import Config
from .core import COMMANDS, Unit, materialize_commands
from .log import init_logger
from .units import import_units

try:
    import uvloop
except ImportError:
    uvloop = None


log = logging.getLogger(__name__)


class Edi(metaclass=Singleton):
    """Main event framework for the bot."""

    loop: asyncio.AbstractEventLoop

    def __init__(self, config: Config = None) -> None:
        self.config = config or Config()
        self.units: Dict[Type[Unit], Unit] = {}
        self.task: Optional[asyncio.Future] = None
        self.command_re = re.compile(r"^@_$")
        self._started = False
        log.debug(f"Edi initialized with {config}")

    def start(self) -> None:
        """Start the asyncio event loop, and close it when we're done."""
        if self._started:
            raise Exception("Edi already started")

        if uvloop and self.config.bot.uvloop:
            log.debug("Using uvloop")
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        self.loop = asyncio.new_event_loop()

        if self.config.bot.debug:
            self.loop.set_debug(True)

        self.loop.add_signal_handler(signal.SIGINT, self.sigterm)
        self.loop.add_signal_handler(signal.SIGTERM, self.sigterm)

        self.task = asyncio.ensure_future(self.run(), loop=self.loop)
        self.loop.run_forever()
        self.loop.close()

    def sigterm(self) -> None:
        """Handle Ctrl-C or SIGTERM by stopping the event loop nicely."""
        log.warning("Signal received, stopping execution")
        asyncio.ensure_future(self.stop(), loop=self.loop)

    async def run(self) -> None:
        """Execute all the bits of Edi."""

        while True:
            try:
                log.debug("connecting to slack")
                self.slack = Slack(token=self.config.bot.token)
                async for event in self.slack.rtm():
                    if event.type == "hello":
                        log.info(
                            f"connected to {self.slack.team.name} "
                            f"as {self.slack.me.name}"
                        )
                        await self.ready()

                    if event.type == "goodbye":
                        log.info("RTM server will disconnect soon")

                    await self.dispatch(event)

                log.info("RTM disconnected")

            except SlackError:
                log.exception("RTM exception, reconnecting")
                continue

            except Exception:
                log.exception("run loop exception, stopping")
                await self.stop()
                raise

    async def ready(self) -> None:
        """Connected to slack and ready to start units."""

        if self.units:
            return

        self.command_re = re.compile(
            r"^\s*"
            rf"(?P<name>@?{self.slack.me.name}|<@{self.slack.me.id}>)[:,]?"
            r"\s+(?P<command>\w+)(?P<args>.*)$"
        )

        import_units()
        self.units = {
            unit: unit(self.slack)
            for unit in Unit.all_units()
            if unit.__name__ not in self.config.units.disable_units
        }
        materialize_commands(self.units)
        log.debug(f"starting {len(self.units)} units")
        for result in await asyncio.gather(
            *[unit.start() for unit in self.units.values()], return_exceptions=True
        ):
            if isinstance(result, BaseException):
                log.error(f"uncaught exception:\n{result}")

    async def stop(self) -> None:
        """Stop all the bits of Edi."""

        try:
            if self.task is not None:
                self.task.cancel()
                self.task = None

            log.debug(f"Stopping {len(self.units)} units")
            for result in await asyncio.gather(
                *[unit.stop() for unit in self.units.values()], return_exceptions=True
            ):
                if isinstance(result, BaseException):
                    log.error(f"uncaught exception:\n{result}")

            await self.slack.close()

        finally:
            self.loop.stop()
            log.info("Goodbye!")

    async def command(self, event: Event) -> bool:
        """Parse for command and dispatch, return True if handled."""
        if event.type != "message" or "subtype" in event or "bot_user" in event:
            return False

        match = self.command_re.match(event.text)
        if not match:
            return False

        log.info(f"possible command: {event.text}")
        user = self.slack.users[event.user]
        channel = self.slack.channels[event.channel]
        command = match[2].strip().lower()
        args = match[3].strip()

        if command not in COMMANDS:
            log.warning(f"unknown command from {user.name}: {command} {args}")
            return False

        try:
            method, args_re, _description = COMMANDS[command]
            if command in self.config.units.disable_commands:
                await self.slack.api(
                    "chat.postMessage",
                    as_user=True,
                    channel=channel.id,
                    text=f'<@{user.id}> command "{command}" disabled',
                )
                return True

            match = args_re.match(args)
            if not match:
                log.warning(f"invalid arguments from {user.name}: {command} {args}")
                await self.slack.api(
                    "chat.postMessage",
                    as_user=True,
                    channel=channel.id,
                    text=f'<@{user.id}> invalid arguments to command "{command}"',
                )
                return True

            kwargs = match.groupdict()
            if kwargs:
                log.info(f"running {method.__name__}({channel}, {user}, **{kwargs})")
                response = await method(channel, user, **kwargs)
            else:
                pargs = match.groups()
                log.info(f"running {method.__name__}({channel}, {user}, *{pargs})")
                response = await method(channel, user, *pargs)

            if response:
                await self.slack.api(
                    "chat.postMessage", as_user=True, channel=channel.id, text=response
                )

        except Exception:
            log.exception("exception occurred during command processing")
            try:
                await self.slack.api(
                    "chat.postMessage",
                    as_user=True,
                    channel=channel.id,
                    text=fr"<@{user.id}> error occurred ¯\_(ツ)_/¯",
                )
            except SlackError:
                log.exception("failed to alert user of error")

        return True

    async def dispatch(self, event: Event) -> None:
        """Dispatch events to all active units."""
        if "channel" in event:
            channel_name = self.slack.channels[event.channel].name
            if channel_name in self.config.bot.ignore_channels:
                log.debug(f"ignoring event from channel #{channel_name}")
                return

        await self.command(event)

        results = await asyncio.gather(
            *[unit.dispatch(event) for unit in self.units.values()],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, BaseException):
                log.error(f"uncaught exception:\n{result}")


def init_from_config(config: Config) -> None:
    """Initialize Edi from a loaded `Config` object."""

    init_logger(stdout=True, file_path=config.bot.log, debug=config.bot.debug)
    log.debug("logger initialized")

    Edi(config).start()
