#!/usr/bin/env python3

import json
import pprint
import urllib.request

debug = False
write_debug = True

with open("debug/access_token", "r") as access_token_file:
    access_token = access_token_file.read()

if debug:
    request = open("debug/newsfeed.json", "rb")
else:
    request = urllib.request.urlopen("https://api.vk.com/method/newsfeed.get?access_token=" + access_token)

with request:
    response = request.read()

if not debug and write_debug:
    with open("debug/newsfeed.json", "wb") as debug_response:
        debug_response.write(response)

response = json.loads(response.decode("utf-8"))

pprint.pprint(response)
