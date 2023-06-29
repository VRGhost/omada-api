import dataclasses
import enum
import functools
import logging
import typing
from datetime import datetime

import requests
import yarl
from requests.cookies import RequestsCookieJar

from . import api_bindings, function_interface_bindings

logger = logging.getLogger(__name__)


def timestamp() -> int:
    """Omada API calls expects timestamp in milliseconds."""
    return int(datetime.utcnow().timestamp() * 1000)


@enum.unique
class CustomErrorCodes(int, enum.Enum):
    """This enum contains fake error codes used by this api module"""

    ImpossibleError = -1  # You should never see this error code
    UnknownSite = 99_001
    UnknownError = 99_999


class OmadaError(Exception):
    """Display errorCode and optional message returned from Omada API."""

    code: int = CustomErrorCodes.ImpossibleError
    msg: str = "<No message>"

    def __init__(self, json):
        error_code = -1
        str_errors = []
        try:
            error_code = int(json["errorCode"])
        except Exception as err:
            str_errors.append(f"Error extracting error code: {err!r}")
            error_code = CustomErrorCodes.UnknownError

        try:
            str_errors.append(json["msg"])
        except Exception as err:
            str_errors.extend(
                [f"Error extracting error message: {err!r}", f"Input json: {json!r}"]
            )

        self.code = error_code
        self.msg = "\n".join(str_errors)

    def __str__(self):
        return f"Omada error: {self.code=}, {self.msg=}"


@enum.unique
class LevelFilter(enum.Enum):  # ruff: noqa: A003
    """Alert and event levels"""

    Error = 0
    Warning = 1
    Information = 2


@dataclasses.dataclass(frozen=True)
class OmadaConfig:
    base_url: yarl.URL
    site: str
    omada_controller_id: typing.Optional[str] = None
    ssl_verify: bool = True


class Omada:
    """The main Omada API class."""

    def __init__(self, config: OmadaConfig):
        self.config = config

        # set up requests session and cookies
        self.session = requests.Session()
        self.session.verify = self.config.ssl_verify
        self.session.cookies = RequestsCookieJar()

    @functools.cached_property
    def omada_controller_id(self) -> str:
        if self.config.omada_controller_id:
            out = self.config.omada_controller_id
        else:
            raise NotImplementedError(
                "TODO: implement fetch from self.baseurl + '/api/info' when talking to the controller locally"
            )
        return out

    @functools.cached_property
    def current_user(self) -> api_bindings.CurrentUser:
        return api_bindings.CurrentUser(**self.get_current_user())

    @property
    def api_root(self) -> yarl.URL:
        return self.config.base_url / self.omada_controller_id / "api" / "v2"

    def _default_request_params(self) -> dict:
        return {"_": timestamp(), "token": self.login_result.token}

    def get_json_response(self, response) -> dict:
        """Post-processing of a generic omada api request"""
        logger.debug(f"Received API response: {response=} {response.text=!r}")
        response.raise_for_status()
        try:
            json = response.json()
        except Exception as err:
            raise OmadaError(
                "\n".join(
                    [
                        "Unable to parse respone json: {err!r}",
                        "Response text:",
                        response.text,
                    ]
                )
            ) from None
        if json.get("errorCode") == 0:
            return json.get("result", None)
        raise OmadaError(json)

    def _find_site(self, name: typing.Optional[str] = None):
        """Look up a site key given the name."""

        # Use the stored site if not provided.
        if name is None:
            name = self.config.site

        # Look for the site in the privilege list.
        for site in self.current_user.privilege.sites:
            if site.name == name:
                return site.key

        raise OmadaError(
            {
                "errorCode": CustomErrorCodes.UnknownSite,
                "msg": f'Current user does not have privilege to site "{name}"',
            }
        )

    def _get(self, path, params: typing.Optional[dict] = None):
        """Perform a GET request and return the result."""
        if not params:
            params = {}
        response = self.session.get(self.api_root / path, params=params)
        return self.get_json_response(response)

    def _patch(
        self,
        path: str,
        params: typing.Optional[dict] = None,
        data: typing.Optional[dict] = None,
        json: typing.Optional[dict] = None,
    ):
        """Perform a PATCH request and return the result."""

        if not params:
            params = {}
        params = params.copy()

        params.update({"_": timestamp(), "token": self.login_result.token})

        response = self.session.patch(
            self.api_root / path, params=params, data=data, json=json
        )
        return self.get_json_response(response)

    def _geterator(
        self, path: str, params: typing.Optional[typing.Dict[str, typing.Any]] = None
    ):
        """Perform a GET request and yield the results."""
        total_rows = 1  # will be updated by the first get call
        last_row_data = [42]  # will be updated by the first get call
        yielded_rows = 0

        if params:
            active_params = params.copy()
        else:
            active_params = {}

        active_params.update(
            {
                "_": timestamp(),
                "token": self.login_result.token,
                "currentPage": 1,
                "currentPageSize": 100,
            }
        )
        while last_row_data and yielded_rows < total_rows:
            resp = self._get(path, active_params)
            last_row_data = resp.get("data", [])
            yield from last_row_data
            yielded_rows += len(last_row_data)
            total_rows = int(resp["totalRows"])
            active_params["currentPage"] += 1

    login_result: typing.Optional[api_bindings.LoginResult] = None

    def login(self, username: str, password: str) -> api_bindings.LoginResult:
        """Log in with the provided credentials and return the result."""
        assert username, "Username must be provided"
        assert password, "Password must be provided"
        # Only try to log in if we're not already logged in.
        if self.login_result is None:
            # Perform the login request manually.
            response = self.session.post(
                self.api_root / "login",
                json={"username": username, "password": password},
            )
            response.raise_for_status()

            # Get the login response.
            json = response.json()
            if json["errorCode"] != 0:
                raise OmadaError(json)

            # Store the login result.
            self.login_result = api_bindings.LoginResult(**json["result"])

            # Store CSRF token header.
            self.session.headers.update({"Csrf-Token": self.login_result.token})

        return self.login_result

    def logout(self):
        """Log out of the current session. Return value is always None."""
        # Only try to log out if we're already logged in.
        if self.login_result is not None:
            # Send the logout request.
            resp = self.session.post(
                self.api_root / "logout", params=self._default_request_params()
            )
            self.get_json_response(resp)
            # Clear the stored result.
            self.login_result = None
            return True

        return False

    def get_login_status(self) -> bool:
        """Returns the current login status."""
        return self._get("loginStatus").get("login", False)

    def get_current_user(self) -> dict:
        """Returns the current user information."""
        return self._get("users/current")

    def get_site_groups(
        self,
        site: typing.Optional[str] = None,
        type: typing.Optional[str] = None,  # ruff: noqa: A002
    ) -> typing.Sequence[dict]:
        """Returns the list of groups for the given site."""
        site_id = self._find_site(site)
        str_type = f"/{type}" if type else ""
        rv = self._get(f"sites/{site_id}/setting/profiles/groups{str_type}")
        return rv.get("data", [])

    def get_portal_candidates(self, site: typing.Optional[str] = None) -> dict:
        """Returns the list of portal candidates for the given site.

        This is the "SSID & Network" list on Settings > Authentication > Portal > Basic Info.
        """
        return self._get(f"sites/{self._find_site(site)}/setting/portal/candidates")

    def get_scenarios(self) -> typing.Iterable[str]:
        """Returns the list of scenarios."""
        return self._get("scenarios")

    def get_sites(self) -> typing.Generator[dict, None, None]:
        """Returns the list of all sites."""
        return self._geterator("sites")

    def get_site_devices(
        self, site: typing.Optional[str] = None
    ) -> typing.Iterable[dict]:
        """Returns the list of devices for given site."""
        return self._get(f"sites/{self._find_site(site)}/devices")

    def get_site_clients(
        self, site: typing.Optional[str] = None, active: typing.Optional[bool] = True
    ) -> typing.Iterable[dict]:
        """Returns the list of active clients for given site."""
        params = {}
        if active in (True, False):
            params["filters.active"] = "true" if active else "false"
        return self._geterator(
            f"sites/{self._find_site(site)}/clients",
            params=params,
        )

    def get_site_alerts(
        self, site: typing.Optional[str] = None, archived: bool = False
    ) -> typing.Iterable[dict]:
        """Returns the list of alerts for given site."""
        params = {"filters.archived": "true" if archived else "false"}

        return self._geterator(f"sites/{self._find_site(site)}/alerts", params=params)

    def get_site_events(self, **kwargs) -> typing.Iterable[dict]:
        """Returns the list of events for given site."""
        settings = function_interface_bindings.SiteEventsInterface(**kwargs)
        all_params = {
            "filters.timeStart": settings.time_start,
            "filters.timeEnd": settings.time_end,
            "filters.module": settings.module,
        }
        # Remove empty filters
        params = {}
        for key, value in all_params.items():
            if value is None:
                continue
            else:
                params[key] = value
        return self._geterator(
            f"sites/{self._find_site(settings.site)}/events", params=params
        )

    def get_site_notifications(
        self, site: typing.Optional[str] = None
    ) -> typing.Iterable[dict]:
        """Returns the notification settings for given site."""
        return self._get(f"sites/{self._find_site(site)}/notification")

    def get_site_settings(self, site: typing.Optional[str] = None) -> dict:
        """Returns the list of settings for the given site."""
        return self._get(f"sites/{self._find_site(site)}/setting")

    def set_site_settings(
        self, site: typing.Optional[str] = None, settings: dict = None
    ) -> bool:
        """Push back the settings for the site.

        (Returns `True` on success)
        """
        if settings is None:
            raise NotImplementedError("Please provide settings dict")
        self._patch(f"sites/{self._find_site(site)}/setting", json=settings)
        return True

    def get_time_ranges(
        self, site: typing.Optional[str] = None
    ) -> typing.Iterable[dict]:
        """Returns the list of timerange profiles for the given site."""
        return self._get(f"sites/{self._find_site(site)}/setting/profiles/timeranges")[
            "data"
        ]

    def get_wireless_groups(self, site: typing.Optional[str] = None):
        """Returns the list of wireless network groups.

        This is the "WLAN Group" list on Settings > Wireless Networks.
        """
        return self._get(f"sites/{self._find_site(site)}/setting/wlans")["data"]

    def get_wireless_networks(
        self, site: typing.Optional[str] = None, group_id: str = None
    ):
        """Returns the list of wireless networks for the given group.

        This is the main SSID list on Settings > Wireless Networks.
        """
        if group_id is None:
            raise NotImplementedError("Please provide group ID")
        return self._geterator(
            f"sites/{self._find_site(site)}/setting/wlans/{group_id}/ssids"
        )
