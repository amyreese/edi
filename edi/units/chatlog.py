# Copyright 2017 John Reese
# Licensed under the MIT license

from ..core import Unit, Message
from ..log import Log


class ChatLog(Unit):

    async def on_hello(self, _message: Message) -> None:
        Log.info("Hello, Slack!")
