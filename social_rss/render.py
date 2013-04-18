"""HTML rendering tools."""

import tornado.escape

escape = tornado.escape.xhtml_escape
"""Escapes a string so it is valid within HTML."""
