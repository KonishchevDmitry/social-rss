"""VK module."""

import functools
import logging
import pprint
import re

from urllib.parse import urlencode

from pycl.core import Error

from social_rss import vk_api
from social_rss.render import block as _block
from social_rss.render import em as _em
from social_rss.render import escape as _escape
from social_rss.render import image as _image
from social_rss.render import image_block as _image_block
from social_rss.render import link as _link
from social_rss.render import quote_block as _quote_block
from social_rss.request import BaseRequestHandler

LOG = logging.getLogger(__name__)


_VK_URL = "https://vk.com/"
"""VK URL."""


_BR_RE = re.compile(r"<br\s*/?>")
"""Matches a <br> tag."""

_TEXT_URL_RE = re.compile(r"(^|\s|>)(https?://[^']+?)(\.?(?:<|\s|$))")
"""Matches a URL in a plain text."""

_DOMAIN_ONLY_TEXT_URL_RE = re.compile(r"(^|\s|>)((?:[a-z0-9](?:[-a-z0-9]*[a-z0-9])?\.)+[a-z0-9](?:[-a-z0-9]*[a-z0-9])/[^']+?)(\.?(?:<|\s|$))")
"""Matches a URL without protocol specification in a plain text."""

_USER_LINK_RE = re.compile(r"\[((?:id|club)\d+)\|([^\]]+)\]")
"""Matches a user link in a post text."""


_CATEGORY_TYPE = "type/"
"""Item type."""

_CATEGORY_TYPE_REPOST = _CATEGORY_TYPE + "repost"
"""Reposted item type."""


_CATEGORY_SOURCE = "source/"
"""Item source."""

_CATEGORY_SOURCE_USER = _CATEGORY_SOURCE + "user/"
"""User item."""

_CATEGORY_SOURCE_GROUP = _CATEGORY_SOURCE + "group/"
"""Group item."""



class RequestHandler(BaseRequestHandler):
    """VK RSS request handler."""

    def get(self):
        """Handles the request."""

        credentials = self._get_credentials()
        if credentials is None:
            self._unauthorized("Please enter VK access_token in password box.")
            return

        try:
            newsfeed = _get_newsfeed(credentials[1])
        except vk_api.ApiError as e:
            if e.code == 5:
                self._unauthorized(str(e))
                return
            else:
                raise

        self._write_rss(newsfeed)



# Internal tools


def _get_newsfeed(access_token):
    """Returns VK news feed."""

    response = vk_api.call(access_token, "newsfeed.get")

    try:
        items = []
        users = _get_users(response["profiles"], response["groups"])

        for api_item in response["items"]:
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

                # This item should be skipped
                if item is None:
                    continue

                item["author"] = _escape(user["name"])
                item.setdefault("categories", set()).update([
                    _CATEGORY_TYPE + api_item["type"],
                    (_CATEGORY_SOURCE_GROUP if user["id"] < 0 else _CATEGORY_SOURCE_USER) + _get_profile_name(user["id"]),
                ])
            except Exception:
                LOG.exception("Failed to process news feed item:\n%s",
                    pprint.pformat(api_item))

                item = {
                    "title": "Внутренняя ошибка сервера",
                    "text":  "При обработке новости произошла внутренняя ошибка сервера",
                }

            item["id"] = "id:{}:{}:{}".format(
                api_item["source_id"], api_item["type"], api_item["date"])
            item["time"] = api_item["date"]

            items.append(item)
    except Exception:
        LOG.exception("Failed to process news feed:\n%s", pprint.pformat(response))
        raise

    return {
        "title":       "ВКонтакте: Новости",
        "url":         _VK_URL,
        "image":       _VK_URL + "press/Simple.png",
        "description": "Новостная лента ВКонтакте",
        "items":       items,
    }


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


def _get_profile_name(user_id):
    """Returns profile name by user id."""

    return ("club" if user_id < 0 else "id") + str(abs(user_id))


def _get_user_url(user_id):
    """Returns profile URL of the specified user."""

    return _VK_URL + _get_profile_name(user_id)


def _vk_id(owner_id, object_id):
    """Returns full ID of an object."""

    return "{}_{}".format(owner_id, object_id)



# Rendering


def _duration(seconds):
    """Renders audio/video duration string."""

    hours = seconds // 60 // 60
    minutes = seconds // 60 % 60
    seconds = seconds % 60

    if hours:
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    else:
        return "{:02d}:{:02d}".format(minutes, seconds)


def _photo(info, big):
    """Renders a photo."""

    return _block(
        _vk_link("photo", _vk_id(info["owner_id"], info["pid"]),
            _image(info["src_big"] if big else info["src"])))


def _vk_link(link_type, target, html):
    """Renders a VK link."""

    return _link(_VK_URL + link_type + target, html)



# Parsing


def _friend_item(users, user, item):
    """Parses a new friend item."""

    html = ""
    for friend in item["friends"][1:]:
        friend = users[friend["uid"]]
        html += _image_block(
            _get_user_url(friend["id"]), friend["photo"],
            _link(_get_user_url(friend["id"]), _escape(friend["name"])))

    return {
        "title": _escape(user["name"] + ": новые друзья"),
        "text":  html,
        "url":   "{}friends?id={}&section=all".format(_VK_URL, user["id"]),
    }


def _note_item(users, user, item):
    """Parses a note item."""

    notes = item["notes"][1:]

    return {
        "title":  _escape(user["name"] + ": заметка"),
        "text":   "".join(
            _block(_em("Заметка: " + _vk_link(
                "note", _vk_id(note["owner_id"], note["nid"]), _escape(note["title"]))))
            for note in notes
        ),
        "url":    _VK_URL + "note" + _vk_id(notes[0]["owner_id"], notes[0]["nid"]),
        "unique": True,
    }


def _parse_text(text):
    """Parses a post text."""

    text = _BR_RE.sub("\n", text.replace("\n", " "))

    html = _escape(text)
    html = _TEXT_URL_RE.sub(r"\1" + _link(r"\2", r"\2") + r"\3", html)
    html = _DOMAIN_ONLY_TEXT_URL_RE.sub(r"\1" + _link(r"http://\2", r"\2") + r"\3", html)
    html = _USER_LINK_RE.sub(_em(_link(_VK_URL + r"\1", r"\2")), html)
    html = html.replace("\n", "<br>")

    return html.strip()


def _photo_item(users, user, item, title):
    """Parses a photo item."""

    photos = item["photos"][1:]

    return {
        "title":  _escape(user["name"] + ": " + title),
        "text":   "".join(_photo(photo, big=len(photos) == 1) for photo in photos),
        "url":    _VK_URL + "photo" + _vk_id(photos[0]["owner_id"], photos[0]["pid"]),
        "unique": True,
    }


def _post_item(users, user, item):
    """Parses a wall post item."""

    attachment_order = (
        "doc",
        "note",
        "page",
        "poll",
        "posted_photo",
        "photo",
        "graffiti",
        "app",
        "video",
        "link",
        "audio",
    )

    def attachment_sort_key(attachment):
        try:
            return attachment_order.index(attachment["type"])
        except ValueError:
            return len(attachment_order)

    top_html = ""
    bottom_html = ""
    categories = set()

    attachments = sorted(
        item.get("attachments", []), key=attachment_sort_key)

    if not item["text"] and not attachments and "geo" in item:
        LOG.debug("Skip check-in item from %s from %s.", user["name"], item["date"])
        return

    if (
        "attachment" in item and
        item["text"] == item["attachment"][item["attachment"]["type"]].get("title")
    ):
        main_html = ""
    else:
        main_html = _parse_text(item["text"])

    photo_count = functools.reduce(
        lambda count, attachment:
            count + ( attachment["type"] in ("app", "graffiti", "photo", "posted_photo") ),
        attachments, 0)
    big_image = photo_count == 1

    for attachment in attachments:
        info = attachment[attachment["type"]]
        add_category = True

        if attachment["type"] == "app":
            top_html += _block(
                _vk_link("app", info["app_id"],
                    _image(info["src_big" if big_image else "src"])))

        elif attachment["type"] == "graffiti":
            top_html += _block(
                _vk_link("graffiti", info["gid"],
                    _image(info["src_big" if big_image else "src"])))


        elif attachment["type"] == "link":
            link_block = _em("Ссылка: " + _link(info["url"], _escape(info["title"])))
            link_description = _parse_text(info["description"]) or _escape(info["title"])

            if "image_src" in info:
                if link_description:
                    link_block += _image_block(info["url"], info["image_src"], link_description)
                else:
                    link_block += _block(_link(info["url"], _image(info["image_src"])))
            elif link_description:
                link_block += _block(link_description)

            top_html += _block(link_block)


        elif attachment["type"] == "photo":
            top_html += _photo(info, big_image)
            add_category = False

        elif attachment["type"] == "posted_photo":
            top_html += _photo(info, big_image)


        elif attachment["type"] == "audio":
            bottom_html += _block(_em(
                "Аудиозапись: " +
                _vk_link("search",
                    "?" + urlencode({
                        "c[q]": info["performer"] + " - " + info["title"],
                        "c[section]": "audio"
                    }),
                    _escape("{} - {} ({})".format(info["performer"], info["title"],
                        _duration(info["duration"]))))))

        elif attachment["type"] == "video":
            top_html += _block(
                _image(info["image"]) +
                _block(_em(_escape("{} ({})".format(
                    info["title"], _duration(info["duration"]))))))


        elif attachment["type"] == "doc":
            top_html += _block(_em(_escape(
                "Документ: {}".format(info["title"]))))

        elif attachment["type"] == "note":
            top_html += _block(_em(_escape(
                "Заметка: {}".format(info["title"]))))

        elif attachment["type"] == "page":
            top_html += _block(_em(_escape(
                "Страница: {}".format(info["title"]))))

        elif attachment["type"] == "poll":
            top_html += _block(_em(_escape(
                "Опрос: {}".format(info["question"]))))


        else:
            LOG.error("Got an unknown attachment type %s with text '%s'",
                attachment, item["text"])


        if add_category:
            categories.add(_CATEGORY_TYPE + attachment["type"])


    html = top_html + main_html + bottom_html

    if "copy_owner_id" in item and "copy_post_id" in item:
        html = _block(
            _em(_link(
                _get_user_url(item["copy_owner_id"]),
                _escape(users[item["copy_owner_id"]]["name"])
            )) + " пишет:"
        ) + html

        if "copy_text" in item:
            html = _quote_block(item["copy_text"], html)

        categories.add(_CATEGORY_TYPE_REPOST)

    html = _image_block(_get_user_url(user["id"]), user["photo"], html)

    return {
        "title":      _escape(user["name"] + ": запись на стене"),
        "text":       html,
        "url":        _VK_URL + "wall" + _vk_id(user["id"], item["post_id"]),
        "unique":     True,
        "categories": categories,
    }
