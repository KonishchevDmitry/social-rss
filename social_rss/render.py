"""HTML rendering tools."""

import io

# Note: Firefox ignores styles when displays RSS.
# So, we limit use of styles and try to use HTML-only properties.


def block(html, style=None):
    """"Renders a text block."""

    if style is None:
        return "<p>" + html + "</p>"
    else:
        return "<p style='{}'>{}</p>".format(style, html)


def em(html):
    """Renders an emphasized text."""

    return "<b>" + html + "</b>"


def image(src):
    """Renders an image."""

    return "<img style='display: block; border-style: none;' src='{}' />".format(src)


def image_block(url, image_src, html):
    """Renders an image block."""

    return table([[ link(url, image(image_src)), html ]])


def link(url, html):
    """Renders a link."""

    return "<a href='{url}'>{html}</a>".format(url=url, html=html)


def quote_block(html, quoted_html):
    """Renders a quote block."""

    return block(html) + block(quoted_html, "margin-left: 1em;")


def table(rows, row_spacing=10, column_spacing=10):
    """Renders a table."""

    with io.StringIO() as html:
        html.write("<table cellpadding='0' cellspacing='0'>")

        for row_id, row in enumerate(rows):
            if row_id:
                html.write("<tr><td height='{}' colspan='{}'></td></tr>".format(
                    row_spacing, len(row) + len(row) // 2))

            html.write("<tr valign='top'>")

            for column_id, column in enumerate(row):
                if column_id:
                    html.write("<td width='{}'></td>".format(column_spacing))
                html.write("<td>" + column + "</td>")

            html.write("</tr>")

        html.write("</table>")

        return html.getvalue()
