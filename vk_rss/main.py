#!/usr/bin/env python3

"""VK RSS main module."""

import logging
import os
import sys

import tornado.ioloop
import tornado.web

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pycl.log

from vk_rss import config
from vk_rss import rss
from vk_rss import tools

LOG = logging.getLogger("vk-rss.main")


class RootHandler(tornado.web.RequestHandler):
    """The server's root handler."""

    def get(self):
        # TODO
        self.set_header("Content-Type", "application/xml")
        newsfeed = tools.get_newsfeed()
        self.write(rss.generate(newsfeed))
        #import pprint
        #self.write(pprint.pformat(newsfeed))


def main():
    """The script"s main function."""

    assert hasattr(config, "PORT")
    assert hasattr(config, "ACCESS_TOKEN")

    if not hasattr(config, "DEBUG_MODE"):
        config.DEBUG_MODE = False
    if not hasattr(config, "WRITE_DEBUG"):
        config.WRITE_DEBUG = False

    pycl.log.setup(debug_mode = True)

    application = tornado.web.Application([
        ("/", RootHandler),
    ], debug=config.DEBUG_MODE)

    application.listen(config.PORT)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
