# Copyright 2017 John Reese
# Licensed under the MIT license

import logging

from ..core import Unit, Message

log = logging.getLogger(__name__)


class ChatLog(Unit):

    async def on_hello(self, _message: Message) -> None:
        log.info("Hello, Slack!")
