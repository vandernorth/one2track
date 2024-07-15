import json
import logging
from typing import List

import requests
from .client_types import (
    TrackerDevice,
    One2TrackConfig,
    AuthenticationError
)

_LOGGER = logging.getLogger(__name__)

CONFIG = {
    "login_url": "https://www.one2trackgps.com/auth/users/sign_in",
    "device_url": "https://www.one2trackgps.com/users/%account%/devices",
    "session_cookie": "_iadmin"
}


class GpsClient():
    config: One2TrackConfig
    cookie: str = ""
    csrf: str = ""

    def __init__(self, config: One2TrackConfig):
        self.config = config

    async def get_csrf(self):
        login_page = requests.get(CONFIG["login_url"])
        if login_page.status_code == 200:
            html = login_page.text
            self.csrf = self.parse_csrf(html)
            print(f"[pre-login] Found this CSRF: {self.csrf}")
            self.cookie = self.parse_cookie(login_page)
            print(f"[pre-login] Found this cookie: {self.cookie}")
        else:
            _LOGGER.warning(f"[pre-log] failed pre-login. response code: {login_page.status_code}")
            raise AuthenticationError("Login page unavailable")

    def parse_cookie(self, response) -> str:
        return response.headers['Set-Cookie'].split(CONFIG["session_cookie"])[1].split(";")[
            0].replace("=", "")

    def parse_csrf(self, html) -> str:
        return html.split("name=\"csrf-token\" content=\"")[1].split("\"")[0]

    async def login(self):
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "cookie": f"_iadmin={self.cookie}"
        }
        login_data = {
            "authenticity_token": self.csrf,
            "user[login]": self.config.username,
            "user[password]": self.config.password,
            "gdpr": "1",
            "user[remember_me]": "1",
        }
        response = requests.post(CONFIG["login_url"], headers=headers, data=login_data, allow_redirects=False)

        print("[login] Status:", response.status_code)

        # login is successful when we get a fresh cookie
        if response.status_code == 302 and "Set-Cookie" in response.headers:
            print("[login] login success!")
            self.cookie = self.parse_cookie(response)
            print(f"[login] Found this cookie: {self.cookie}")
        else:
            _LOGGER.warning(f"[gps] failed to login. response code: {response.status_code}")
            raise AuthenticationError("Invalid username or password")

    async def update(self) -> List[TrackerDevice]:
        if self.cookie:
            print("already logged in, continue...")
        else:
            await self.get_csrf()
            await self.login()

        try:
            devices = await self.get_device_data()

            # update attributes
            for _device in devices:
                device = _device['device']
                print("[device] device found:", device['uuid'], device['name'])

            return devices

        except AuthenticationError:
            print("login failed")
            self.cookie = ""
            self.csrf = ""
            # hopefully next update loop login will be better

    async def get_device_data(self):
        headers = {'content-type': 'application/json', 'Accept': 'application/json'}
        cookies = {'accepted_cookies': 'true', '_iadmin': self.cookie}
        url = CONFIG["device_url"].replace("%account%", self.config.id)
        response = requests.get(url, headers=headers, cookies=cookies)
        rawjson = response.text

        print("[devices] raw json:", response.status_code, rawjson)
        devices = json.loads(rawjson)

        return devices
