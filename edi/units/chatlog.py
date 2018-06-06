# Copyright 2017 John Reese
# Licensed under the MIT license

import logging

from aioslack import Event
from datetime import datetime
from pathlib import Path

from edi import Edi, Unit

log = logging.getLogger(__name__)


class ChatLog(Unit):
    async def start(self) -> None:
        config = Edi().config
        self.root = Path(config.chatlog_root).expanduser()
        self.format = config.chatlog_format

    def log_message(self, channel: str, dt: datetime, message: str) -> None:
        # todo: replace <@U0HML87RT> with @username

        date = dt.strftime(r"%Y-%m-%d")
        time = dt.strftime(r"%H:%M:%S")

        formatted = self.format.format(
            date=date,
            time=time,
            team=self.slack.team.name,
            channel=channel,
            message=message,
        )
        log.info(f"[{date} {time}] #{channel} {message}")

        filename = self.root / channel / f"{date}.log"
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "a") as f:
            f.write(formatted + "\n")

    async def on_hello(self, event: Event) -> None:
        assert event
        self.root /= self.slack.team.name
        self.root.mkdir(parents=True, exist_ok=True)
        log.info(f"logging messages to {self.root}")

    async def on_message(self, event: Event) -> None:
        dt = datetime.fromtimestamp(float(event.ts))

        channel = self.slack.channels[event.channel].name
        message = ""
        if "bot_user" in event:
            username = event.username
        elif "user" in event:
            username = self.slack.users[event.user].name
        else:
            username = "unknown"

        if "subtype" in event:
            subtype = event.subtype

            if subtype == "bot_message":
                message = f"<{username}> {event.text}"
            elif subtype == "me_message":
                message = f"* {username} {event.text}"
            elif subtype == "channel_join":
                message = f"* {username} joined the channel"
            elif subtype == "channel_leave":
                message = f"* {username} left the channel"
            elif subtype == "channel_purpose":
                message = f"* {username} set the channel purpose: {event.purpose}"
            elif subtype == "channel_topic":
                message = f"* {username} set the channel topic: {event.topic}"
            elif subtype == "channel_name":
                message = (
                    f"* {username} renamed the channel from "
                    f"{event.old_name} to {event.name}"
                )

        else:
            message = f"<{username}> {event.text}"

        if message:
            self.log_message(channel, dt, message)

    async def on_reaction_added(self, event: Event) -> None:
        ts = float(event.item["ts"])
        dt = datetime.fromtimestamp(ts)
        channel = event.item["channel"]
        history = await self.slack.api(
            "channels.history", channel=channel, latest=ts, oldest=ts, inclusive=True
        )
        context = Event.generate(history.messages[0])
        channel = self.slack.channels[channel].name
        reactor = self.slack.users[event.user].name
        username = self.slack.users[context.user].name
        text = context.text
        if len(text) > 40:
            text = text[:40].rsplit(" ", 1)[0] + "..."
        message = f" * {reactor} reacted :{event.reaction}: to <{username}> {text}"

        self.log_message(channel, dt, message)
