import json
import logging
from typing import List
from aiohttp import ClientSession
from .client_types import (
    TrackerDevice,
    One2TrackConfig,
    AuthenticationError
)
from ..common import (
     VERSION
)

_LOGGER = logging.getLogger(__name__)

#https://www.one2trackgps.com/devices/0a078c6a-6433-4439-9e5e-5f9726e54f2a/messages | device_message[message]: test
CONFIG = {
    "login_url": "https://www.one2trackgps.com/auth/users/sign_in",
    "base_url": "https://www.one2trackgps.com/",
    "device_url": "https://www.one2trackgps.com/users/%account%/devices",
    "api_function_url": "https://www.one2trackgps.com/api/devices/%uuid%/functions",
    "message_url": "https://www.one2trackgps.com/devices/%uuid%/messages",
    "session_cookie": "_iadmin"
}


class GpsClient():
    config: One2TrackConfig
    cookie: str = ""
    csrf: str = ""
    account_id: str
    session: ClientSession

    def __init__(self, config: One2TrackConfig, session: ClientSession = None):
        self.config = config
        self.account_id = config.id  # might be empty
        self.session = session

    def set_account_id(self, account_id):
        self.account_id = account_id

    async def get_csrf(self):
        login_page = await self.call_api(CONFIG["login_url"])
        if login_page.status == 200:
            html = await login_page.text()
            self.csrf = self.parse_csrf(html)
            _LOGGER.debug(f"[pre-login] Found this CSRF: {self.csrf}")
            self.cookie = self.parse_cookie(login_page)
            _LOGGER.debug(f"[pre-login] Found this cookie: {self.cookie}")
        else:
            _LOGGER.warning(f"[pre-log] failed pre-login. response code: {login_page.status}")
            raise AuthenticationError("Login page unavailable")

    async def get_csrf_nologin(self):
        url = CONFIG["device_url"].replace("%account%", self.account_id)
        page = await self.call_api(url)
        if page.status == 200:
            html = await page.text()
            self.csrf = self.parse_csrf(html)
            _LOGGER.debug(f"[nologin] Found this CSRF: {self.csrf}")
        else:
            _LOGGER.warning(f"[nologin] failed to retrieve csrf. response code: {page.status}")

    async def call_api(self, url: str, data=None, allow_redirects=True, use_json=False):
        headers = {}
        cookies = {'accepted_cookies': 'true'}

        if data is not None:
            headers["content-type"] = "application/x-www-form-urlencoded"

        if use_json:
            headers["content-type"] = "application/json"
            headers["Accept"] = "application/json"

        if self.cookie:
            cookies['_iadmin'] = self.cookie

        _LOGGER.debug('[http] %s %s %s', url, headers, cookies)

        if self.session is None:
            self.session = ClientSession()

        self.session.cookie_jar.clear()

        if data is not None:
            return await self.session.post(url,
                                           data=data,
                                           headers=headers,
                                           allow_redirects=allow_redirects,
                                           cookies=cookies
                                           )
        else:
            return await self.session.get(url, headers=headers, allow_redirects=allow_redirects, cookies=cookies)

    def parse_cookie(self, response) -> str:
        cookie = ""
        if 'Set-Cookie' in response.headers:
            cookie = response.headers['Set-Cookie']

        if cookie:
            try:
                return response.headers['Set-Cookie'].split(CONFIG["session_cookie"])[1].split(";")[
                    0].replace("=", "")
            except (IndexError, KeyError) as e:
                _LOGGER.error(f"Failed to parse session cookie: {e}")
                return ""
        else:
            _LOGGER.warning(f"No new cookie found {self.cookie} was the old cookie")
            return ""

    def parse_csrf(self, html) -> str:
        try:
            return html.split("name=\"csrf-token\" content=\"")[1].split("\"")[0]
        except IndexError:
            _LOGGER.error("Failed to parse CSRF token from HTML - page structure may have changed")
            raise AuthenticationError("Could not find CSRF token on login page")

    async def login(self):
        login_data = {
            "authenticity_token": self.csrf,
            "user[login]": self.config.username,
            "user[password]": self.config.password,
            "gdpr": "1",
            "user[remember_me]": "1",
        }
        response = await self.call_api(CONFIG["login_url"], data=login_data, allow_redirects=False)

        _LOGGER.debug("[login] Status: %s", response.status)

        # login is successful when we get a fresh cookie
        if response.status == 302 and "Set-Cookie" in response.headers:
            _LOGGER.debug("[login] login success!")
            self.cookie = self.parse_cookie(response)
            _LOGGER.debug(f"[login] Found this cookie: {self.cookie}")
            _LOGGER.debug(f"[login] Found this redirect: {response.headers['Location']}")
        else:
            _LOGGER.warning(f"[gps] failed to login. response code: {response.status}")
            raise AuthenticationError("Invalid username or password")

    async def get_user_id(self):
        response = await self.call_api(CONFIG["base_url"], allow_redirects=False)
        url = response.headers['Location']
        account_id = url.split('/')[4]
        _LOGGER.debug(f'[install] extracted {account_id} from {url}')
        self.set_account_id(account_id)
        return account_id

    async def install(self):
        await self.get_csrf()
        await self.login()
        id = await self.get_user_id()
        return id

    async def update(self) -> List[TrackerDevice]:
        if self.cookie:
            _LOGGER.debug("already logged in, continue... %s", self.cookie)
            _LOGGER.debug("TEST123")
            _LOGGER.debug("Version: %s", VERSION)
        else:
            _LOGGER.debug("renew login")
            await self.get_csrf()
            await self.login()
            await self.get_user_id()

        try:
            devices = await self.get_device_data()
            return devices

        except AuthenticationError:
            _LOGGER.warning("login failed")
            self.cookie = ""
            self.csrf = ""
            # hopefully next update loop login will be better

    async def get_device_data(self):
        url = CONFIG["device_url"].replace("%account%", self.account_id)
        response = await self.call_api(url, use_json=True)
        rawjson = await response.text()

        #_LOGGER.debug("[devices] raw json: %s %s", response.status, rawjson)

        if response.status == 200:
            try:
                devices = json.loads(rawjson)
                return list(map(lambda x: x['device'], devices))
            except Exception as e:
                _LOGGER.error("[one2track][error][update] Cannot parse JSON: %s | %s", rawjson, e)
                return None
        else:
            _LOGGER.error(f"[one2track][error][update] Cant get devices updated: code: %s message: %s", response.status,
                          rawjson)
            self.cookie = ""
            self.csrf = ""
            # hopefully next update loop login will be better
            return []

    async def set_device_refresh_location(self, uuid):
       await self.send_device_command(uuid, "0039")

       return True

    async def send_device_command(self, uuid, cmd_code, cmd_value=None, cmd_value_param=None):
       await self.get_csrf_nologin()

       post_data = {
                    "function[code]": cmd_code,
                    "authenticity_token": self.csrf,
               }

       if(cmd_value):
            if(cmd_value_param):
                post_data[cmd_value_param] = cmd_value
            else:
                post_data["function[cmd_value][]"] = cmd_value

       url = CONFIG["api_function_url"].replace("%account%", self.account_id).replace("%uuid%", uuid)

       _LOGGER.debug("[send_device_command] url: %s", url)
       _LOGGER.debug("[send_device_command] post_data: %s", post_data)

       response = await self.call_api(url, post_data)
       rawjson = await response.text()

       _LOGGER.debug("[send_device_command] response raw json: %s %s", response.status, rawjson)

       return True


    async def send_device_message(self, uuid, message):
       await self.get_csrf_nologin()

       post_data = {
                    "device_message[message]": message,
                    "authenticity_token": self.csrf,
               }

       url = CONFIG["message_url"].replace("%uuid%", uuid)

       _LOGGER.debug("[send_device_command] url: %s", url)
       _LOGGER.debug("[send_device_command] post_data: %s", post_data)

       response = await self.call_api(url, post_data)
       rawjson = await response.text()

       _LOGGER.debug("[send_device_command] response raw json: %s %s", response.status, rawjson)

       return True

    async def close(self):
        await self.session.close()
