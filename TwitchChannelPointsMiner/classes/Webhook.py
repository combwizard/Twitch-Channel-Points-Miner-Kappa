from textwrap import dedent
from urllib.parse import urlencode, urlparse, urlunparse

import requests

from TwitchChannelPointsMiner.classes.Settings import Events


class Webhook(object):
    __slots__ = ["endpoint", "method", "events"]

    def __init__(self, endpoint: str, method: str, events: list):
        self.endpoint = endpoint
        self.method = method
        self.events = [str(e) for e in events]

    def send(self, message: str, event: Events) -> None:
        
        if str(event) in self.events:
            parsed = urlparse(self.endpoint)
            query = urlencode({"event_name": str(event), "message": message})
            if parsed.query:
                query = f"{parsed.query}&{query}"
            url = urlunparse(parsed._replace(query=query))

            if self.method.lower() == "get":
                requests.get(url=url)
            elif self.method.lower() == "post":
                requests.post(url=url)
            else:
                raise ValueError("Invalid method, use POST or GET")
