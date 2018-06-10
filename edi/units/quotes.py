# Copyright 2017 John Reese
# Licensed under the MIT license

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

import aiosqlite
from attr import dataclass

from aioslack.types import Channel, Event, User
from edi import Config, Edi, Unit, command

from .twitter import Twitter

log = logging.getLogger(__name__)


@dataclass
class quotes(Config):
    db_path: str = "quotes.db"
    tweet_grabs: bool = False
    tweet_format: str = "<{user}> {text}"


@dataclass
class Quote:
    id: int
    channel: str
    username: str
    added_by: str
    added_at: datetime
    text: str

    @classmethod
    def new(cls, channel: str, username: str, added_by: str, text: str) -> "Quote":
        now = datetime.fromtimestamp(int(time.time()))
        return Quote(
            id=0,
            channel=channel,
            username=username,
            added_by=added_by,
            added_at=now,
            text=text,
        )


class QuoteDB:
    def __init__(self, path: str) -> None:
        self.path = path
        self.db = aiosqlite.connect(path, isolation_level=None)

    async def start(self) -> None:
        await self.db.__aenter__()

        async with self.db.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY,
                    channel TEXT,
                    username TEXT,
                    added_by TEXT,
                    added_at TIMESTAMP,
                    quote TEXT
                )
                """
            )
            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS quote_channel
                ON quotes (channel)
                """
            )
            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS quote_username
                ON quotes (username)
                """
            )

    async def stop(self) -> None:
        await self.db.__aexit__(None, None, None)

    async def add(self, quote: Quote) -> int:
        query = """
            INSERT INTO quotes
            VALUES (NULL, ?, ?, ?, ?, ?)
        """

        async with self.db.execute(
            query,
            [quote.channel, quote.username, quote.added_by, quote.added_at, quote.text],
        ) as cursor:
            quote.id = cursor.lastrowid
            return quote.id

    async def get(self, qid: int) -> Quote:
        query = """
            SELECT * FROM quotes
            WHERE id = ?
        """
        async with self.db.execute(query, [qid]) as cursor:
            if not cursor.rowcount:
                raise KeyError(f"quote id {qid} not found")
            row = await cursor.fetchone()
            return Quote(*row)

    async def find(
        self, channel: str, username: str = "", fuzz: bool = False, limit: int = 0
    ) -> List[Quote]:
        if username:
            query = """
                SELECT * FROM quotes
                WHERE channel = ? AND username LIKE ?
                ORDER BY id DESC
            """
            params = [channel, f"{username[:5]}%" if fuzz else username]
        else:
            query = """
                SELECT * FROM quotes
                WHERE channel = ?
                ORDER BY id DESC
            """
            params = [channel]

        if limit > 0:
            query += " LIMIT ? "
            params += [limit]

        async with self.db.execute(query, params) as cursor:
            result: List[Quote] = []
            async for row in cursor:
                result.append(Quote(*row))
            return result

    async def random(
        self, channel: str, username: str = "", fuzz: bool = False
    ) -> Quote:
        if username:
            query = """
                SELECT * FROM quotes
                WHERE channel = ? AND username LIKE ?
                ORDER BY random()
                LIMIT 1
            """
            params = [channel, f"{username[:5]}%" if fuzz else username]
        else:
            query = """
                SELECT * FROM quotes
                WHERE channel = ?
                ORDER BY random()
                LIMIT 1
            """
            params = [channel]

        async with self.db.execute(query, params) as cursor:
            if not cursor.rowcount:
                return Quote.new(channel, "nobody", "nobody", "say something funny")
            row = await cursor.fetchone()
            return Quote(*row)


class Quotes(Unit):
    async def start(self) -> None:
        self.config = Edi().config.quotes
        self.db = QuoteDB(self.config.db_path)
        await self.db.start()

        self.recents: Dict[str, Dict[str, str]] = defaultdict(dict)

    @command(
        r"(?P<username>\S+)", description="<username>: grab the user's last message"
    )
    async def grab(self, channel: Channel, user: User, username: str) -> str:
        username = self.slack.decode(username, prefix="")
        text = self.recents[channel.name].get(username, None)
        if text is None:
            return f"no history for {username}"

        q = Quote.new(channel.name, username, user.name, text)
        await self.db.add(q)

        if self.config.tweet_grabs:
            try:
                twitter = Edi().units.get(Twitter, None)
                if twitter is not None:
                    tweet = self.config.tweet_format.format(
                        id=q.id, channel=q.channel, username=q.username, text=q.text
                    )
                    await twitter.update(tweet)
                    return f"quote #{q.id} saved and tweeted"

                else:
                    log.debug(f"Twitter unit not active")

            except Exception:
                log.exception(f"failed to tweet quote #{q.id}")

        return f"quote #{q.id} saved"

    @command(
        r"(?:#?(?P<qid>\d+)|(?P<limit>\d+)?\s*(?P<username>\S+))?",
        description="""
            [<id> | [<count>] <username>]: show recent quotes

            id: integer - show a specific quote by ID
            count: integer - how many quotes to show
            username: string - only show quotes for the given username
        """,
    )
    async def quote(
        self,
        channel: Channel,
        user: User,
        *,
        qid: str = "",
        username: str = "",
        limit: str = "",
    ) -> str:
        username = self.slack.decode(username, prefix="")
        qs = []
        if qid:
            qid = int(qid)
            q = await self.db.get(qid)
            if q.channel == channel.name:
                qs = [q]
        else:
            if limit:
                limit = int(limit)
                limit = max(1, min(20, limit))
            else:
                limit = 3
            qs = await self.db.find(channel.name, username, fuzz=True, limit=limit)
        if not qs:
            return "no quotes found"
        return "\n".join(f"#{q.id} [{q.added_at}] <{q.username}> {q.text}" for q in qs)

    async def on_message(self, event: Event) -> None:
        if "user" not in event or "subtype" in event:
            return

        channel = self.slack.channels[event.channel].name
        username = self.slack.users[event.user].name
        self.recents[channel][username] = event.text

    async def stop(self) -> None:
        await self.db.stop()
