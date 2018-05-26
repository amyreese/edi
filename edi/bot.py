# Copyright 2017 John Reese
# Licensed under the MIT license

import asyncio
import logging
import signal

try:
    import uvloop
except ImportError:
    uvloop = None

from aioslack import Event, Slack
from ent import Singleton
from typing import List

from .config import Config
from .core import Unit
from .log import init_logger
from .units import import_units

log = logging.getLogger(__name__)


class Edi(metaclass=Singleton):
    """Main event framework for the bot."""

    loop: asyncio.AbstractEventLoop

    def __init__(self, config: Config) -> None:
        log.debug(f"initializing with {config}")
        self.config = config
        self.units: List[Unit] = []

        self._started = False

    def start(self) -> None:
        """Start the asyncio event loop, and close it when we're done."""
        if self._started:
            raise Exception("Edi already started")

        if uvloop and self.config.uvloop:
            log.debug("Using uvloop")
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        self.loop = asyncio.new_event_loop()

        if self.config.debug:
            self.loop.set_debug(True)

        self.loop.add_signal_handler(signal.SIGINT, self.sigterm)
        self.loop.add_signal_handler(signal.SIGTERM, self.sigterm)

        asyncio.ensure_future(self.run(), loop=self.loop)
        self.loop.run_forever()
        self.loop.close()

    def sigterm(self) -> None:
        """Handle Ctrl-C or SIGTERM by stopping the event loop nicely."""
        log.warning("Signal received, stopping execution")
        asyncio.ensure_future(self.stop(), loop=self.loop)

    async def run(self) -> None:
        """Execute all the bits of Edi."""

        try:
            self.slack = Slack(token=self.config.token)

            import_units()
            self.units = [unit(self.slack) for unit in Unit.all_units()]
            log.debug(f"Starting {len(self.units)} units")
            await asyncio.gather(*[unit.start() for unit in self.units])

            log.debug(f"Starting RTM loop")
            async for event in self.slack.rtm():
                await self.dispatch(event)

        except Exception:
            log.exception(f"run loop exception, stopping")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop all the bits of Edi."""

        try:
            log.debug(f"Stopping {len(self.units)} units")
            await asyncio.gather(
                *[unit.stop() for unit in self.units], return_exceptions=True
            )

            await self.slack.close()

        finally:
            self.loop.stop()
            log.info("Goodbye!")

    async def dispatch(self, event: Event) -> None:
        """Dispatch events to all active units."""
        results = await asyncio.gather(
            *[unit.dispatch(event) for unit in self.units], return_exceptions=True
        )

        for result in results:
            if isinstance(result, BaseException):
                log.error(f"uncaught exception:\n{result}")


def init_from_config(config: Config) -> None:
    """Initialize Edi from a loaded `Config` object."""

    init_logger(stdout=True, file_path=config.log, debug=config.debug)
    log.debug("logger initialized")

    Edi(config).start()
