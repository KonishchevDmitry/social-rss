#!/usr/bin/env python3

# TODO

import cgi
import json
import logging
import os
import pprint
import urllib.parse
import urllib.request

import pycl.log
from pycl.core import Error

LOG = logging.getLogger("vk-rss")


# TODO
DEBUG = False
WRITE_DEBUG = True
ACCESS_TOKEN = None


def main():
    """The script"s main function."""

    global ACCESS_TOKEN

    pycl.log.setup(debug_mode = True)

    with open("access_token", "r") as access_token_file:
        ACCESS_TOKEN = access_token_file.read().strip()

    response = _api("newsfeed.get")

    #pprint.pprint(response)


def _api(method, **kwargs):
    """Calls the specified VK API method."""

    kwargs.setdefault("language", "0")
    kwargs.setdefault("access_token", ACCESS_TOKEN)

    url = "https://api.vk.com/method/{}?".format(method) + urllib.parse.urlencode(kwargs)
    debug_path = os.path.join("debug", method + ":" + urllib.parse.urlencode(kwargs))

    LOG.debug("Sending VK API request: %s...", url)

    try:
        if DEBUG:
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

                if WRITE_DEBUG:
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


if __name__ == "__main__":
    main()
