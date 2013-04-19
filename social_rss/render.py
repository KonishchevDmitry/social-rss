"""HTML rendering tools."""

import tornado.escape

# Note: Firefox ignores styles when displays RSS. So, it's better to limit use
# of styles.


def block(html, style=None):
    """"Renders a text block."""

    if style is None:
        return "<p>" + html + "</p>"
    else:
        return "<p style='{}'>{}</p>".format(style, html)


def em(html):
    """Renders an emphasized text."""

    return "<b>" + html + "</b>"


escape = tornado.escape.xhtml_escape
"""Escapes a string so it is valid within HTML."""


def image(src):
    """Renders an image."""

    return "<img style='display: block; border-style: none;' src='{}' />".format(escape(src))


def image_block(url, image_src, html):
    """Renders an image block."""

    return (
        "<table cellpadding='0' cellspacing='0'>"
            "<tr valign='top'>"
                "<td>{image}</td><td width='10'></td><td>{html}</td>"
            "</tr>"
        "</table>"
    ).format(image=link(url, image(image_src)), html=html)


def link(url, html):
    """Renders a link."""

    return "<a href='{url}'>{html}</a>".format(url=escape(url), html=html)


def quote_block(html, quoted_html):
    """Renders a quote block."""

    return block(html) + block(quoted_html, "margin-left: 1em;")
