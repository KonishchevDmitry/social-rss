"""Twitter module."""

import json
import logging
import os
import pprint

# TODO: add to README
from twitter import OAuth, Twitter

from social_rss import config
from social_rss.request import BaseRequestHandler

LOG = logging.getLogger(__name__)


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
                response = json.loads(debug_response.read().decode())
        else:
            api = Twitter(
                auth=OAuth(
                    access_token_key, access_token_secret,
                    consumer_key, consumer_secret))

            response = api.statuses.home_timeline()

            if config.WRITE_OFFLINE_DEBUG:
                with open(debug_path, "wb") as debug_response:
                    debug_response.write(json.dumps(response).encode())

        pprint.pprint(response)

        #self._write_rss(newsfeed)
