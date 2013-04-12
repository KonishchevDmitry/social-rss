"""Tools for getting various data from VK."""

import datetime
import logging
import pprint
import re

from urllib.parse import urlencode

from vk_rss import api

LOG = logging.getLogger("vk-rss.tools")


_VK_URL = "http://vk.com/"
"""VK URL."""


_TEXT_URL_RE = re.compile(r"(^|\s|>)(https?://[^']+?)(\.?(?:<|\s|$))")
"""Matches a URL in a plain text."""

_DOMAIN_ONLY_TEXT_URL_RE = re.compile(r"(^|\s|>)((?:[a-z0-9](?:[-a-z0-9]*[a-z0-9])?\.)+[a-z0-9](?:[-a-z0-9]*[a-z0-9])/[^']+?)(\.?(?:<|\s|$))")
"""Matches a URL without protocol specification in a plain text."""

_USER_LINK_RE = re.compile(r"\[((?:id|club)\d+)\|([^\]]+)\]")
"""Matches a user link in a post text."""


def _get_users(profiles, groups):
    """Maps profiles and groups to their IDs."""

    users = {}

    for profile in profiles:
        users[profile["uid"]] = {
            "id":    profile["uid"],
            "login": profile["screen_name"],
            "name":  profile["first_name"] + " " + profile["last_name"],
            "photo": profile["photo"],
        }

    for group in groups:
        users[-group["gid"]] = {
            "id":    -group["gid"],
            "login": group["screen_name"],
            "name":  group["name"],
            "photo": group["photo"],
        }

    return users



# Formatting


def _block(text):
    """"Renders a text block."""

    return "<p>" + text + "</p>"


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


def _link(url, text):
    """Renders a link."""

    return "<a href='{url}'>{text}</a>".format(url=url, text=text)


def _link_block(url, image_src, description):
    """Renders a link block."""

    return (
        "<table cellpadding='0' cellspacing='0'>"
            "<tr valign='top'>"
                "<td>{image}</td>"
                "<td style='padding-left: 10px;'>{description}</td>"
            "</tr>"
        "</table>"
    ).format(image=_link(url, _image(image_src)), description=description)


def _parse_text(text):
    """Parses a post text."""

    text = _TEXT_URL_RE.sub(r"\1<a href='\2'>\2</a>\3", text)
    text = _DOMAIN_ONLY_TEXT_URL_RE.sub(r"\1<a href='http://\2'>\2</a>\3", text)
    text = _USER_LINK_RE.sub(r"<b><a href='{}\1'>\2</a></b>".format(_VK_URL), text)

    return text.strip()


def _vk_link(link_type, target, text):
    """Renders a VK link."""

    return _link(_VK_URL + link_type + target, text)



# TODO HERE



def get_newsfeed():
    response = api.call("newsfeed.get")
#    pprint.pprint(response["groups"][0])
    pprint.pprint(response["items"][0])
#    pprint.pprint(response["profiles"][0])

    users = _get_users(response["profiles"], response["groups"])
    api_items = response["items"]
    del response

#    pprint.pprint(users)

    # TODO: don't change source
    items = []
    for item in api_items:
        supported = []
        unsupported = []

        user = users[item["source_id"]]
        title = user["name"]

        if item["type"] == "post":
            text = item["text"]

            if "attachment" in item and item["text"] == item["attachment"][item["attachment"]["type"]].get("title"):
                text = ""

            attachments = item.get("attachments", [])
            big_image = len(attachments) > 1 # TODO
            #photo_count = functools.reduce(
            #    lambda count, attachment:
            #        count + ( attachment["type"] in ( "photo", "posted_photo" ) ),
            #    attachments, 0)

            for attachment in attachments:
                info = attachment[attachment["type"]]

                if attachment["type"] == "app":
                    supported.append(_vk_link("app", info["app_id"],
                        _image(info["src_big" if big_image else "src"])))
                elif attachment["type"] == "graffiti":
                    supported.append(_vk_link("graffiti", info["gid"],
                        _image(info["src_big" if big_image else "src"])))
                elif attachment["type"] == "link":
                    # TODO 
                    description = _parse_text(info["description"]) or info["title"]

                    html = _em("Ссылка: " + _link(info["url"], info["title"]))

                    if info.get("image_src") and description:
                        html += _link_block(info["url"], info["image_src"], description)
                    elif info.get("image_src"):
                        html += _block(_link(info["url"], _image(info["image_src"])))
                    elif description:
                        html += _block(description)

                    supported.append(html)
                elif attachment["type"] in ("photo", "posted_photo"):
                    photo_src = info["src_big"] if big_image else info["src"]

                    # Photo may have id = 0 and owner_id = 0 if it for example
                    # generated by an application.
                    if info["pid"] == 0 or info["owner_id"] == 0:
                        supported.append(
                            _vk_link("wall", "{}_{}".format(user["id"], item["post_id"], _image(photo_src))))
                    else:
                        supported.append(
                            _vk_link(
                                "wall", "{user_id}_{post_id}?z=photo{owner_id}_{photo_id}%2Fwall{user_id}_{post_id}".format(
                                    user_id=user["id"], post_id=item["post_id"], owner_id=info["owner_id"], photo_id=info["pid"]),
                                _image(photo_src)))
                elif attachment["type"] == "video":
                    supported.append(
                        _vk_link("video", "{}_{}".format(info["owner_id"], info["vid"]),
                            _image(info["image"]) +
                            _em("{} ({})".format(info["title"], _duration(info["duration"])))))
                elif attachment["type"] == "audio":
                    unsupported.append(_em(
                        "Аудиозапись: " +
                        _vk_link("search",
                            "?" + urlencode({
                                "c[q]": info["performer"] + " - " + info["title"],
                                "c[section]": "audio"
                            }),
                            "{} - {} ({})".format(info["performer"], info["title"],
                                _duration(info["duration"])))))
                elif attachment["type"] == "doc":
                    unsupported.append(_em(
                        "Документ: {}".format(info["title"])))
                elif attachment["type"] == "note":
                    unsupported.append(_em(
                        "Заметка: {}".format(info["title"])))
                elif attachment["type"] == "page":
                    unsupported.append(_em(
                        "Страница: {}".format(info["title"])))
                elif attachment["type"] == "poll":
                    unsupported.append(_em(
                        "Опрос: {}".format(info["question"])))
                else:
                    TODO
        else:
            # TODO
            continue

        if supported:
            text += "<p>" + "</p><p>".join(supported) + "</p>"

#        text += _parse_text(item["text"])

        if unsupported:
            text += "<p>" + "</p><p>".join(unsupported) + "</p>"

#        if "copy_owner_id" in item and "copy_post_id" in item:
#            text = "<p><b><a href="{profile_url}">{user_name}</a></b> пишет:</p>".format(
#                profile_url = _get_profile_url(item["copy_owner_id"]), user_name = users[item["copy_owner_id"]]["name"]) + text
#
#            if "copy_text" in item:
#                text = "<p>{}</p><div style="margin-left: 1em;">{}</div>".format(item["copy_text"], text)
#
#        if "reply_owner_id" in item and "reply_post_id" in item:
#            text += (
#                "<p><i>"
#                    "В ответ на <a href="{vk_url}wall{item[reply_owner_id]}_{item[reply_post_id]}">запись</a> "
#                    "пользователя <b><a href="{profile_url}">{user_name}</a></b>."
#                "</i></p>".format(vk_url = _VK_URL, item = item,
#                    profile_url = _get_profile_url(item["reply_owner_id"]), user_name = users[item["reply_owner_id"]]["name"]))
#
#        if show_photo:
#            text = (
#                "<table cellpadding="0" cellspacing="0"><tr valign="top">"
#                    "<td><a href="{url}"><img {img_style} src="{photo}" /></a></td>"
#                    "<td style="padding-left: 10px;">{text}</td>"
#                "</tr></table>".format(
#                    url = _get_profile_url(item["from_id"]), img_style = img_style,
#                    photo = users[item["from_id"]]["photo"], text = text))

        date = (
            datetime.datetime.fromtimestamp(item["date"])
            # Take MSK timezone into account
            + datetime.timedelta(hours = 4))

        items.append({
            "title": title,
#            "url":   "{0}wall{1}_{2}".format(_VK_URL, user["id"], item["post_id"]),
            "text":  text,
            "date":  date,
        })

    return {
#        "url":        _VK_URL + profile_name,
#        "user_name":  user["name"],
#        "user_photo": user["photo"],
        "items":      items,
    }
