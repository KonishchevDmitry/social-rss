#!/usr/bin/env python3

"""VK RSS main module."""

import logging
import os
import pprint
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pycl.log

from vk_rss import config
from vk_rss import tools

LOG = logging.getLogger("vk-rss.main")


def main():
    """The script"s main function."""

    assert hasattr(config, "ACCESS_TOKEN")
    if not hasattr(config, "DEBUG_MODE"):
        config.DEBUG_MODE = False
    if not hasattr(config, "WRITE_DEBUG"):
        config.WRITE_DEBUG = False

    pycl.log.setup(debug_mode = True)

    pprint.pprint(tools.get_newsfeed())


if __name__ == "__main__":
    main()
