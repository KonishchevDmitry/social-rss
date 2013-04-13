"""VK module."""

import base64
import binascii
import functools
import logging
import re

from urllib.parse import urlencode

import tornado.web

from pycl.core import Error

import social_rss.rss
from social_rss import vk_api

LOG = logging.getLogger(__name__)


_VK_URL = "https://vk.com/"
"""VK URL."""


_TEXT_URL_RE = re.compile(r"(^|\s|>)(https?://[^']+?)(\.?(?:<|\s|$))")
"""Matches a URL in a plain text."""

_DOMAIN_ONLY_TEXT_URL_RE = re.compile(r"(^|\s|>)((?:[a-z0-9](?:[-a-z0-9]*[a-z0-9])?\.)+[a-z0-9](?:[-a-z0-9]*[a-z0-9])/[^']+?)(\.?(?:<|\s|$))")
"""Matches a URL without protocol specification in a plain text."""

_USER_LINK_RE = re.compile(r"\[((?:id|club)\d+)\|([^\]]+)\]")
"""Matches a user link in a post text."""



# Internal tools


def _get_users(profiles, groups):
    """Maps profiles and groups to their IDs."""

    users = {}

    for profile in profiles:
        users[profile["uid"]] = {
            "id":    profile["uid"],
            "name":  profile["first_name"] + " " + profile["last_name"],
            "photo": profile["photo"],
        }

    for group in groups:
        users[-group["gid"]] = {
            "id":    -group["gid"],
            "name":  group["name"],
            "photo": group["photo"],
        }

    return users


def _get_user_url(user_id):
    """Returns profile URL of the specified user."""

    return _VK_URL + ("club" if user_id < 0 else "id") + str(abs(user_id))


def _vk_id(owner_id, object_id):
    """Returns full ID of an object."""

    return "{}_{}".format(owner_id, object_id)



# Rendering
#
# Note: Firefox ignores styles when displays RSS. So, it's better to limit use
# of styles.


def _block(text, style=None):
    """"Renders a text block."""

    if style is None:
        return "<p>" + text + "</p>"
    else:
        return "<p style='{}'>{}</p>".format(style, text)


def _duration(seconds):
    """Renders audio/video duration string."""

    hours = seconds // 60 // 60
    minutes = seconds // 60 % 60
    seconds = seconds % 60

    if hours:
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    else:
        return "{:02d}:{:02d}".format(minutes, seconds)


def _em(text):
    """Renders an emphasized text."""

    return "<b>" + text + "</b>"


def _image(src):
    """Renders an image."""

    return "<img style='display: block; border-style: none;' src='{}' />".format(src)


def _image_block(url, image_src, text):
    """Renders an image block."""

    return (
        "<table cellpadding='0' cellspacing='0'>"
            "<tr valign='top'>"
                "<td>{image}</td><td width='10'></td><td>{text}</td>"
            "</tr>"
        "</table>"
    ).format(image=_link(url, _image(image_src)), text=text)


def _link(url, text):
    """Renders a link."""

    return "<a href='{url}'>{text}</a>".format(url=url, text=text)


def _photo(info, big):
    """Renders a photo."""

    return _block(
        _vk_link("photo", _vk_id(info["owner_id"], info["pid"]),
            _image(info["src_big"] if big else info["src"])))


def _quote_block(text, quoted_text):
    """Renders a quote block."""

    return _block(text) + _block(quoted_text, "margin-left: 1em;")


def _vk_link(link_type, target, text):
    """Renders a VK link."""

    return _link(_VK_URL + link_type + target, text)



# Parsing


def _friend_item(users, user, item):
    """Parses a new friend item."""

    text = ""
    for friend in item["friends"][1:]:
        friend = users[friend["uid"]]
        text += _image_block(
            _get_user_url(friend["id"]), friend["photo"],
            _link(_get_user_url(friend["id"]), friend["name"]))

    return {
        "title": user["name"] + ": новые друзья",
        "text":  text,
        "url":   "{}friends?id={}&section=all".format(_VK_URL, user["id"]),
    }


def _note_item(users, user, item):
    """Parses a note item."""

    notes = item["notes"][1:]

    return {
        "title":  user["name"] + ": заметка",
        "text":   "".join(
            _block(_em("Заметка: " + _vk_link(
                "note", _vk_id(note["owner_id"], note["nid"]), note["title"])))
            for note in notes
        ),
        "url":    _VK_URL + "note" + _vk_id(notes[0]["owner_id"], notes[0]["nid"]),
        "unique": True,
    }


def _parse_text(text):
    """Parses a post text."""

    text = _TEXT_URL_RE.sub(r"\1" + _link(r"\2", r"\2") + r"\3", text)
    text = _DOMAIN_ONLY_TEXT_URL_RE.sub(r"\1" + _link(r"http://\2", r"\2") + r"\3", text)
    text = _USER_LINK_RE.sub(_em(_link(_VK_URL + r"\1", r"\2")), text)

    return text.strip()


def _photo_item(users, user, item, title):
    """Parses a photo item."""

    photos = item["photos"][1:]

    return {
        "title":  user["name"] + ": " + title,
        "text":   "".join(_photo(photo, big=len(photos) == 1) for photo in photos),
        "url":    _VK_URL + "photo" + _vk_id(photos[0]["owner_id"], photos[0]["pid"]),
        "unique": True,
    }


def _post_item(users, user, item):
    """Parses a wall post item."""

    top_text = ""
    bottom_text = ""

    if (
        "attachment" in item and
        item["text"] == item["attachment"][item["attachment"]["type"]].get("title")
    ):
        main_text = ""
    else:
        main_text = item["text"]

    attachments = item.get("attachments", [])

    photo_count = functools.reduce(
        lambda count, attachment:
            count + ( attachment["type"] in ("app", "graffiti", "photo", "posted_photo") ),
        attachments, 0)
    big_image = photo_count == 1

    for attachment in attachments:
        info = attachment[attachment["type"]]

        if attachment["type"] == "app":
            top_text += _block(
                _vk_link("app", info["app_id"],
                    _image(info["src_big" if big_image else "src"])))

        elif attachment["type"] == "graffiti":
            top_text += _block(
                _vk_link("graffiti", info["gid"],
                    _image(info["src_big" if big_image else "src"])))


        elif attachment["type"] == "link":
            link_block = _em("Ссылка: " + _link(info["url"], info["title"]))
            link_description = _parse_text(info["description"]) or info["title"]

            if "image_src" in info:
                if link_description:
                    link_block += _image_block(info["url"], info["image_src"], link_description)
                else:
                    link_block += _block(_link(info["url"], _image(info["image_src"])))
            elif link_description:
                link_block += _block(link_description)

            top_text += _block(link_block)


        elif attachment["type"] in ("photo", "posted_photo"):
            top_text += _photo(info, big_image)


        elif attachment["type"] == "audio":
            bottom_text += _block(_em(
                "Аудиозапись: " +
                _vk_link("search",
                    "?" + urlencode({
                        "c[q]": info["performer"] + " - " + info["title"],
                        "c[section]": "audio"
                    }),
                    "{} - {} ({})".format(info["performer"], info["title"],
                        _duration(info["duration"])))))

        elif attachment["type"] == "video":
            top_text += _block(
                _image(info["image"]) +
                _block(_em("{} ({})".format(info["title"], _duration(info["duration"])))))


        elif attachment["type"] == "doc":
            bottom_text += _block(_em(
                "Документ: {}".format(info["title"])))

        elif attachment["type"] == "note":
            bottom_text += _block(_em(
                "Заметка: {}".format(info["title"])))

        elif attachment["type"] == "page":
            bottom_text += _block(_em(
                "Страница: {}".format(info["title"])))

        elif attachment["type"] == "poll":
            bottom_text += _block(_em(
                "Опрос: {}".format(info["question"])))


        else:
            LOG.error("Got an unknown attachment type %s with text '%s'",
                attachment, item["text"])


    text = top_text + _parse_text(main_text) + bottom_text

    if "copy_owner_id" in item and "copy_post_id" in item:
        text = _block(
            _em(_link(
                _get_user_url(item["copy_owner_id"]),
                users[item["copy_owner_id"]]["name"]
            )) + " пишет:"
        ) + text

        if "copy_text" in item:
            text = _quote_block(item["copy_text"], text)

    text = _image_block(_get_user_url(user["id"]), user["photo"], text)

    return {
        "title":  user["name"] + ": запись на стене",
        "text":   text,
        "url":    _VK_URL + "wall" + _vk_id(user["id"], item["post_id"]),
        "unique": True,
    }



# TODO HERE
import http.client


class RequestHandler(tornado.web.RequestHandler):
    """The server's root handler."""

    def get(self):
        access_token = None
        if "Authorization" in self.request.headers:
            authorization = self.request.headers["Authorization"]
            if authorization.startswith("Basic "):
                try:
                    authorization = base64.b64decode(authorization[len("Basic "):].encode()).decode()
                    if ":" in authorization:
                        access_token = authorization.split(":")[1].strip()
                        LOG.error(access_token)
                except binascii.Error:
                    pass

        if not access_token:
            self.__unauthorized()
            return

        try:
            newsfeed = _get_newsfeed(access_token)
        except vk_api.ApiError as e:
            if e.code == 5:
                self.__unauthorized()
            else:
                raise
        else:
            self.set_header("Content-Type", "application/xml")
            self.write(social_rss.rss.generate(newsfeed))
            #import pprint
            #self.write(pprint.pformat(newsfeed))

    def __unauthorized(self):
        self.set_header("WWW-Authenticate", 'Basic realm="insert realm"')
        self.set_status(http.client.UNAUTHORIZED)

def _get_newsfeed(access_token):
    response = vk_api.call(access_token, "newsfeed.get")

    users = _get_users(response["profiles"], response["groups"])
    api_items = response["items"]
    del response

    items = []
    for api_item in api_items:
        try:
            user = users[api_item["source_id"]]

            if api_item["type"] == "post":
                item = _post_item(users, user, api_item)
            elif api_item["type"] == "photo":
                item = _photo_item(users, user, api_item, "новые фотографии")
            elif api_item["type"] == "photo_tag":
                item = _photo_item(users, user, api_item, "новые отметки на фотографиях")
            elif api_item["type"] == "wall_photo":
                item = _photo_item(users, user, api_item, "новые фотографии на стене")
            elif api_item["type"] == "friend":
                item = _friend_item(users, user, api_item)
            elif api_item["type"] == "note":
                item = _note_item(users, user, api_item)
            else:
                raise Error("Unknown news item type.")

            item["author"] = user["name"]
        except Exception:
            LOG.exception("Failed to process news feed item %s.", api_item)

            item = {
                "title": "Внутренняя ошибка сервера",
                "text":  "При обработке новости произошла внутренняя ошибка сервера",
            }

        # TODO: id, url
        item["id"] = "{}:{}:{}".format(api_item["source_id"], api_item["type"], api_item["date"])
        item["time"] = api_item["date"]
        items.append(item)

    return {
        "title":       "ВКонтакте: Новости",
        "url":         _VK_URL,
        "image":       _VK_URL + "press/Simple.png",
        "description": "Новостная лента ВКонтакте",
        "items":      items,
    }
