"""Base class for all request handlers."""

import base64
import binascii
import http.client

import tornado.web

import social_rss.rss


class BaseRequestHandler(tornado.web.RequestHandler):
    """Base class for all request handlers."""

    def _get_credentials(self):
        """Returns HTTP Basic Access Authentication credentials."""

        if "Authorization" not in self.request.headers:
            return

        authorization = self.request.headers["Authorization"]
        if not authorization.startswith("Basic "):
            return

        authorization = authorization[len("Basic "):]

        try:
            authorization = base64.b64decode(
                authorization.encode()).decode()
        except binascii.Error:
            return

        if ":" not in authorization:
            return

        return authorization.split(":", 1)


    def _unauthorized(self, error):
        """Requests authorization from client."""

        self.set_header("WWW-Authenticate", 'Basic realm="{}"'.format(error.replace('"', "'")))
        self.set_status(http.client.UNAUTHORIZED)


    def _write_rss(self, feed):
        """Writes the specified RSS feed to the output buffer."""

        self.set_header("Content-Type", "application/rss+xml")
        self.write(social_rss.rss.generate(feed))
