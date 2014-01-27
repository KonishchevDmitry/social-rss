"""Twitter module."""

# Note: Twitter HTML-escapes all the data it sends by API.

import calendar
import json
import logging
import os
import pprint

from urllib.parse import urlencode

import dateutil.parser
from twitter import OAuth, Twitter

from social_rss import config
from social_rss.render import block as _block
from social_rss.render import image as _image
from social_rss.render import image_block as _image_block
from social_rss.render import link as _link
from social_rss.request import BaseRequestHandler

LOG = logging.getLogger(__name__)


_TWITTER_URL = "https://twitter.com/"
"""Twitter URL."""


class RequestHandler(BaseRequestHandler):
    """Twitter RSS request handler."""

    def get(self):
        """Handles the request."""

        separator = "_"
        credentials = self._get_credentials()

        if (
            credentials is None or
            separator not in credentials[0] or separator not in credentials[1]
        ):
            self._unauthorized(
                "Please enter your Twitter credentials: "
                "user=$consumer_key{0}$consumer_secret, "
                "password=$access_token_key{0}$access_token_secret.".format(separator))
            return

        consumer, access_token = credentials
        consumer_key, consumer_secret = consumer.split(separator, 1)
        access_token_key, access_token_secret = access_token.split(separator, 1)

        if config.OFFLINE_DEBUG_MODE or config.WRITE_OFFLINE_DEBUG:
            debug_path = os.path.join(config.OFFLINE_DEBUG_PATH,
                "twitter:" + ":".join(credentials))

        if config.OFFLINE_DEBUG_MODE:
            with open(debug_path, "rb") as debug_response:
                timeline = json.loads(debug_response.read().decode())
        else:
            api = Twitter(
                auth=OAuth(
                    access_token_key, access_token_secret,
                    consumer_key, consumer_secret))

            timeline = api.statuses.home_timeline(_timeout=config.API_TIMEOUT)

            if config.WRITE_OFFLINE_DEBUG:
                with open(debug_path, "wb") as debug_response:
                    debug_response.write(json.dumps(timeline).encode())

        try:
            feed = _get_feed(timeline)
        except Exception:
            LOG.exception("Failed to process Twitter timeline:%s", pprint.pformat(timeline))
            raise

        self._write_rss(feed)


def _get_feed(timeline):
    """Generates a feed from timeline."""

    items = []

    for tweet in timeline:
        item = { "id": tweet["id_str"] }

        try:
            item["time"] = int(calendar.timegm(dateutil.parser.parse(tweet["created_at"]).utctimetuple()))

            if tweet.get("retweeted_status") is None:
                real_tweet = tweet
                item["title"] = tweet["user"]["name"]
            else:
                real_tweet = tweet["retweeted_status"]
                item["title"] = "{} (retweeted by {})".format(
                    real_tweet["user"]["name"], tweet["user"]["name"])

            item["url"] = _twitter_user_url(real_tweet["user"]["screen_name"]) + "/status/" + real_tweet["id_str"]

            item["text"] = _image_block(
                _twitter_user_url(real_tweet["user"]["screen_name"]),
                real_tweet["user"]["profile_image_url_https"],
                _parse_text(real_tweet["text"], real_tweet["entities"]))
        except Exception:
            LOG.exception("Failed to process the following tweet:\n%s",
                pprint.pformat(tweet))

            item.setdefault("title", "Internal server error")
            item.setdefault("text",  "Internal server error has occurred during processing this tweet")

        items.append(item)

    return {
        "title":       "Twitter",
        "url":         _TWITTER_URL,
        "image":       _TWITTER_URL + "images/resources/twitter-bird-light-bgs.png",
        "description": "Twitter timeline",
        "items":       items,
    }


def _parse_text(text, tweet_entities):
    """Parses a tweet text."""

    sorted_entities = []

    for entity_type, entities in tweet_entities.items():
        for entity in entities:
            sorted_entities.append(( entity_type, entity ))

    sorted_entities.sort(
        key=lambda entity_tuple: entity_tuple[1]["indices"][0], reverse=True)


    html = ""
    media_html = ""
    pos = len(text)

    for entity_type, entity in sorted_entities:
        start, end = entity["indices"]

        if end < pos:
            html = text[end:pos] + html

        if entity_type == "urls":
            html = _link(entity["expanded_url"], entity["display_url"]) + html
        elif entity_type == "user_mentions":
            html = _link(_twitter_user_url(entity["screen_name"]), entity["name"]) + html
        elif entity_type == "hashtags":
            html = _link(_TWITTER_URL + "search?" + urlencode({ "q": "#" + entity["text"] }), text[start:end]) + html
        elif entity_type == "media":
            html = _link(entity["expanded_url"], entity["display_url"]) + html
            media_html += _block(_link(entity["expanded_url"], _image(entity["media_url_https"])))
        else:
            LOG.error("Unknown tweet entity:\n%s", pprint.pformat(entity))
            html = text[start:end] + html

        pos = start

    if pos:
        html = text[:pos] + html

    return _block(html) + media_html


def _twitter_user_url(screen_name):
    """Returns URL of the specified user profile."""

    return _TWITTER_URL + screen_name
