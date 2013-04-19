"""Twitter module."""

import json
import logging
import os
import pprint
import time

from urllib.parse import urlencode

import dateutil.parser
from twitter import OAuth, Twitter

from social_rss import config
from social_rss.render import block as _block
from social_rss.render import escape as _escape
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

        # TODO
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

            # TODO
            timeline = api.statuses.home_timeline(count=200)

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
        item = { "id":  tweet["id_str"] }

        try:
            item["time"] = int(time.mktime(dateutil.parser.parse(tweet["created_at"]).timetuple()))

            if "retweeted_status" in tweet:
                real_tweet = tweet["retweeted_status"]
                item["title"] = _escape("{} (retweeted by {})".format(
                    real_tweet["user"]["name"], tweet["user"]["name"]))
            else:
                real_tweet = tweet
                item["title"] = _escape(tweet["user"]["name"])

            item["url"] = _twitter_user_url(real_tweet["user"]["screen_name"]) + "/status/" + real_tweet["id_str"] # TODO
            html = _parse_text(real_tweet["text"], real_tweet["entities"])

            html = _image_block(real_tweet["user"]["screen_name"],
                real_tweet["user"]["profile_image_url_https"], html)

            item["text"] = html
        except Exception:
            LOG.exception("Failed to process the following tweet:\n%s",
                pprint.pformat(tweet))

            # TODO
            item.setdefault("title", "Internal server error")
            item.setdefault("text",  "Internal server error has occurred during processing this tweet")

        items.append(item)


    # TODO
    return {
        "title":       "Twitter",
        "url":         _TWITTER_URL,
        "image":       _TWITTER_URL + "images/resources/twitter-bird-light-bgs.png",
        "description": "Twitter timeline",
        "items":       items,
    }


def _parse_text(text, orig_entities):
    sorted_entities = []

    for entity_type, entities in orig_entities.items():
        for entity in entities:
            entity = entity.copy()
            entity["type"] = entity_type
            sorted_entities.append(entity)

    sorted_entities.sort(key=lambda entity: entity["indices"][0], reverse=True)

    html = ""
    media = ""
    cur_pos = len(text)

    for entity in sorted_entities:
        start, end = entity["indices"]

        if end < cur_pos:
            html = _escape(text[end:cur_pos]) + html

        if entity["type"] == "user_mentions":
            html = _link(_twitter_user_url(entity["screen_name"]), _escape(entity["name"])) + html
        elif entity["type"] == "hashtags":
            html = _link(_TWITTER_URL + "search?" + urlencode({ "q": entity["text"], "src": "hash" }), _escape(text[start:end])) + html
        elif entity["type"] == "urls":
            html = _link(entity["expanded_url"], _escape(entity["display_url"])) + html
        elif entity["type"] == "media":
            html = _link(entity["expanded_url"], _escape(entity["display_url"])) + html
            media += _block(_link(entity["expanded_url"], _image(entity["media_url_https"])))
        else:
            LOG.error("Unknown tweet entity:\n%s", pprint.pformat(entity))
            html = _escape(text[start:end]) + html

        cur_pos = start

    if cur_pos:
        html = _escape(text[:cur_pos]) + html

    return _block(html) + media


def _twitter_user_url(screen_name):
    """Returns URL of the specified user."""

    return _TWITTER_URL + screen_name # TODO
