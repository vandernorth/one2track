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
    "base_url": "https://www.one2trackgps.com/",
    "device_url": "https://www.one2trackgps.com/users/%account%/devices",
    "session_cookie": "_iadmin"
}


class GpsClient():
    config: One2TrackConfig
    cookie: str = ""
    csrf: str = ""
    account_id: str

    def __init__(self, config: One2TrackConfig):
        self.config = config
        self.account_id = config.id  # might be empty

    def set_account_id(self, account_id):
        self.account_id = account_id

    async def get_csrf(self):
        login_page = await self.call_api(CONFIG["login_url"])
        if login_page.status_code == 200:
            html = login_page.text
            self.csrf = self.parse_csrf(html)
            print(f"[pre-login] Found this CSRF: {self.csrf}")
            self.cookie = self.parse_cookie(login_page)
            print(f"[pre-login] Found this cookie: {self.cookie}")
        else:
            _LOGGER.warning(f"[pre-log] failed pre-login. response code: {login_page.status_code}")
            raise AuthenticationError("Login page unavailable")

    async def call_api(self, url: str, data=None, allow_redirects=True, use_json=False):
        func = requests.get if data is None else requests.post
        headers = {}
        cookies = {}

        if data is not None:
            headers["content-type"] = "application/x-www-form-urlencoded"

        if use_json:
            headers["content-type"] = "application/json"
            headers["Accept"] = "application/json"

        if self.cookie:
            # headers["cookie"] = f"_iadmin={self.cookie}"
            cookies = {'accepted_cookies': 'true', '_iadmin': self.cookie}

        print('call', url, headers, func)
        return func(url, data=data, headers=headers, allow_redirects=allow_redirects, cookies=cookies)

    def parse_cookie(self, response) -> str:
        return response.headers['Set-Cookie'].split(CONFIG["session_cookie"])[1].split(";")[
            0].replace("=", "")

    def parse_csrf(self, html) -> str:
        return html.split("name=\"csrf-token\" content=\"")[1].split("\"")[0]

    async def login(self):
        login_data = {
            "authenticity_token": self.csrf,
            "user[login]": self.config.username,
            "user[password]": self.config.password,
            "gdpr": "1",
            "user[remember_me]": "1",
        }
        response = await self.call_api(CONFIG["login_url"], data=login_data, allow_redirects=False)

        print("[login] Status:", response.status_code)

        # login is successful when we get a fresh cookie
        if response.status_code == 302 and "Set-Cookie" in response.headers:
            print("[login] login success!")
            self.cookie = self.parse_cookie(response)
            print(f"[login] Found this cookie: {self.cookie}")
            print(f"[login] Found this redirect: {response.headers['Location']}")
        else:
            _LOGGER.warning(f"[gps] failed to login. response code: {response.status_code}")
            raise AuthenticationError("Invalid username or password")

    async def get_user_id(self):
        response = await self.call_api(CONFIG["base_url"], allow_redirects=False)
        url = response.headers['Location']
        account_id = url.split('/')[4]
        print(f'[install] extracted {account_id} from {url}')
        self.set_account_id(account_id)
        return account_id

    async def install(self):
        await self.get_csrf()
        await self.login()
        id = await self.get_user_id()
        return id

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
        url = CONFIG["device_url"].replace("%account%", self.account_id)
        response = await self.call_api(url, use_json=True)
        rawjson = response.text

        print("[devices] raw json:", response.status_code, rawjson)
        devices = json.loads(rawjson)

        return devices
