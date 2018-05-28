# Copyright 2017 John Reese
# Licensed under the MIT license

import asyncio
import logging
import time

from aioslack.types import Auto, Channel, User
from peony import PeonyClient
from peony.exceptions import PeonyException
from typing import Optional

from edi import Edi, Unit, command

log = logging.getLogger(__name__)


@command("tweet", description="<status>: twitter a new tweet")
class Twitter(Unit):

    async def start(self) -> None:
        self.config = Edi().config
        if not all(
            [
                self.config.twitter_consumer_key,
                self.config.twitter_consumer_secret,
                self.config.twitter_access_key,
                self.config.twitter_access_secret,
            ]
        ):
            log.debug(f"missing twitter credentials")
            return

        self.client = PeonyClient(
            consumer_key=self.config.twitter_consumer_key,
            consumer_secret=self.config.twitter_consumer_secret,
            access_token=self.config.twitter_access_key,
            access_token_secret=self.config.twitter_access_secret,
        )

        user = await self.client.user
        log.info(f"connected to twitter as @{user.screen_name}")

        self.task = asyncio.ensure_future(self.timeline())

    async def timeline(self) -> None:
        """Run loop, poll for updates and push new posts to slack."""

        if not self.config.twitter_timeline_channels:
            log.info(f"no twitter timeline channels configured")
            return

        since_id = None

        while True:
            ts = time.time()

            try:
                kwargs = {"count": 20, "include_entities": False}
                if since_id is None:
                    kwargs["count"] = 1
                else:
                    kwargs["since_id"] = since_id

                tweets = await self.client.api.statuses.home_timeline.get(**kwargs)
                if tweets:
                    log.info(f"timeline:")
                    for tweet in reversed(tweets):
                        log.info(f" @{tweet.user.screen_name}: {tweet.text}")
                    tweet = Auto.generate(tweets[-1])

                    if since_id is not None:
                        for name in self.config.twitter_timeline_channels:
                            channel = self.slack.channels.get(name, None)
                            if channel:
                                await self.announce(channel, tweet)

                    since_id = tweet.id_str

                else:
                    log.info(f"timeline empty")

            except PeonyException:
                log.exception("timeline update failed")

            except Exception:
                log.exception(r"¯\_(ツ)_/¯")

            finally:
                wait = (ts + 90) - time.time()
                if wait > 0:
                    log.info(f"sleeping for {wait}s")
                    await asyncio.sleep(wait)

    @staticmethod
    def tweet_url(tweet: Auto) -> str:
        return (
            f":rooster: https://twitter.com/{tweet.user.screen_name}"
            f"/status/{tweet.id_str}"
        )

    async def announce(self, channel: Channel, tweet: Auto) -> None:
        await self.slack.api(
            "chat.postMessage",
            channel=channel.id,
            text=self.tweet_url(tweet),
            as_user=True,
        )

    async def update(self, status: str) -> Optional[Auto]:
        try:
            response = await self.client.api.statuses.update.post(status=status)
            return Auto.generate(response)

        except PeonyException:
            log.exception("failed to update status")
            return None

    async def tweet(self, channel: Channel, user: User, status: str) -> str:
        tweet = await self.update(status)
        if tweet is not None:
            return self.tweet_url(tweet)
        return r"¯\_(ツ)_/¯"

    async def stop(self) -> None:
        self.task.cancel()
