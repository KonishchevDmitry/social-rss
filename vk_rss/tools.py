"""Tools for getting various data from VK."""

from vk_rss import api

def get_newsfeed():
    return api.call("newsfeed.get")
