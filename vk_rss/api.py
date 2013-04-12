"""VK API client."""

import cgi
import json
import logging
import os
import urllib.request
from urllib.parse import urlencode

from pycl.core import Error

from vk_rss import config

LOG = logging.getLogger("vk-rss.api")

_VK_API_URL = "https://api.vk.com/"
"""VK API URL."""


def call(method, **kwargs):
    """Calls the specified VK API method."""

    # TODO
    kwargs.setdefault("count", "100")
    kwargs.setdefault("language", "0")
    kwargs.setdefault("access_token", config.ACCESS_TOKEN)

    url = _VK_API_URL + "method/{}?".format(method) + urlencode(kwargs)
    if config.DEBUG_MODE or config.WRITE_DEBUG:
        debug_path = os.path.join("debug", method + ":" + urlencode(sorted(kwargs.items())))

    LOG.debug("Sending VK API request: %s...", url)

    try:
        if config.DEBUG_MODE:
            with open(debug_path, "rb") as debug_response:
                response = json.loads(debug_response.read().decode())
        else:
            request = urllib.request.Request(url, headers={ "Accept-Language": "ru,en" })

            with urllib.request.urlopen(request) as http_response:
                content_type = http_response.getheader("content-type")
                if content_type is None:
                    raise Error("The server returned a response without Content-Type header.")

                content_type, content_type_opts = cgi.parse_header(content_type)
                if content_type != "application/json":
                    raise Error("The server returned a response with an invalid Content-Type ({}).", content_type)

                response = http_response.read()

                if config.WRITE_DEBUG:
                    with open(debug_path, "wb") as debug_response:
                        debug_response.write(response)

                try:
                    response = json.loads(response.decode(content_type_opts.get("charset", "utf-8")))
                except Exception as e:
                    raise Error("Error while parsing the server's response: {}", e)

        if "error" in response or "response" not in response:
            error = response.get("error", {}).get("error_msg", "").strip()

            if not error:
                error = "Unknown error"

            raise Error("The server returned an error: {}", error)

        return response["response"]
    except Exception as e:
        raise Error("Failed to process {} VK API request: {}", method, e)
