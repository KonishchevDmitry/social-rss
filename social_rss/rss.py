"""Generates an RSS."""

import os
import re
import time

import xml.sax.saxutils

import tornado.template

from social_rss import config


TEMPLATE_LOADER = tornado.template.Loader(os.path.dirname(__file__), autoescape=None)
"""Template loader."""


def generate(feed):
    """Generates an RSS."""

    rss =  TEMPLATE_LOADER.load("rss.rss").generate(
        feed=feed, date=_date, escape=xml.sax.saxutils.escape)

    if not config.DEBUG_MODE:
        rss = re.sub(br">\s+<", b"><", rss)

    return rss


def _date(timestamp):
    """Formats the specified timestamp according to RFC 822."""

    week_day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    month_name = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    year, month, day, hour, min, sec, wday, yday, isdst = time.gmtime(timestamp)

    return "{wday}, {day:02d} {month} {year:4d} {hour:02d}:{min:02d}:{sec:02d} GMT".format(
        wday=week_day_name[wday], day=day, month=month_name[month-1],
        year=year, hour=hour, min=min, sec=sec)
