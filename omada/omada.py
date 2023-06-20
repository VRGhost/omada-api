import dataclasses
import enum
import functools
import logging
import typing
from datetime import datetime

import requests
import yarl
from requests.cookies import RequestsCookieJar

from . import api_bindings

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


@enum.unique
class ModuleFilter(enum.Enum):
    """Alert and event modules"""

    Operation = 0
    System = 1
    Device = 2
    Client = 3


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
        return self.get_current_user()

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

    def _get(self, path):
        """Perform a GET request and return the result."""

        response = self.session.get(
            self.api_root / path,
        )
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

    def __hasData(self, result):
        """Return True if a result contains data."""
        return (result is not None) and ("data" in result) and (len(result["data"]) > 0)

    def _getPaged(self, path, params={}, data=None, json=None):
        """Perform a paged GET request and return the result."""
        if self.login_result is None:
            raise ConnectionError("not logged in")

        if not isinstance(params, dict):
            raise TypeError("params must be a dictionary")

        params["_"] = timestamp()
        params["token"] = self.login_result["token"]

        params.setdefault("currentPage", 1)
        params.setdefault("currentPageSize", 10)

        response = self.session.get(
            self.api_root / path, params=params, data=data, json=json
        )
        response.raise_for_status()

        json = response.json()
        if json["errorCode"] == 0:
            json["result"]["path"] = path
            json["result"]["params"] = params
            return json["result"]

        raise OmadaError(json)

    def __nextPage(self, result):
        """Returns the next page of data if more is available."""
        if "path" in result:
            path = result["path"]
            del result["path"]
        else:
            return None

        if "params" in result:
            params = result["params"]
            del result["params"]
        else:
            return None

        totalRows = int(result["totalRows"])
        currentPage = int(result["currentPage"])
        currentSize = int(result["currentSize"])
        dataLength = len(result["data"])

        if dataLength + (currentPage - 1) * currentSize >= totalRows:
            return None

        params["currentPage"] = currentPage + 1
        return self._getPaged(path, params)

    ##
    ## Perform a GET request and yield the results.
    ##
    def __geterator(self, path, params={}, data=None, json=None):
        result = self._getPaged(path, params, data, json)
        while self.__hasData(result):
            for item in result["data"]:
                yield item
            result = self.__nextPage(result)

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

    def get_current_user(self):
        """Returns the current user information."""
        return api_bindings.CurrentUser(**self._get("users/current"))

    def get_site_groups(
        self, site: typing.Optional[str] = None, type: typing.Optional[str] = None
    ) -> typing.Sequence[api_bindings.SiteGroup]:
        """Returns the list of groups for the given site."""
        site_id = self._find_site(site)
        str_type = f"/{type}" if type else ""
        rv = self._get(f"sites/{site_id}/setting/profiles/groups{str_type}")
        return [api_bindings.SiteGroup(**el) for el in rv.get("data", [])]

    def getPortalCandidates(self, site: typing.Optional[str] = None):
        """Returns the list of portal candidates for the given site.

        This is the "SSID & Network" list on Settings > Authentication > Portal > Basic Info.
        """
        return self._get(f"sites/{self._find_site(site)}/setting/portal/candidates")

    def get_radius_profiles(self, site: typing.Optional[str] = None):
        """Returns the list of RADIUS profiles for the given site."""
        return self._get(f"sites/{self._find_site(site)}/setting/radiusProfiles")

    def get_scenarios(self):
        """Returns the list of scenarios."""
        return self._get("scenarios")

    ##
    ## Returns the list of all sites.
    ##
    def getSites(self):
        return self._geterator("/sites")

    ##
    ## Returns the list of devices for given site.
    ##
    def getSiteDevices(self, site=None):
        return self._get(f"/sites/{self.__findKey(site)}/devices")

    ##
    ## Returns the list of active clients for given site.
    ##
    def getSiteClients(self, site=None):
        return self._geterator(
            f"/sites/{self.__findKey(site)}/clients", params={"filters.active": "true"}
        )

    ##
    ## Returns the list of alerts for given site.
    ##
    def getSiteAlerts(
        self, site=None, archived=False, level=None, module=None, searchKey=None
    ):
        params = {"filters.archived": "true" if archived else "false"}

        if level is not None:
            if level not in ValidLevelFilters:
                raise TypeError("invalid level filter")
            params["filters.level"] = level

        if module is not None:
            if level not in ValidModuleFilters:
                raise TypeError("invalid module filter")
            params["filters.module"] = module

        if searchKey is not None:
            params["searchKey"] = searchKey

        return self._geterator(f"/sites/{self.__findKey(site)}/alerts", params=params)

    ##
    ## Returns the list of events for given site.
    ##
    def getSiteEvents(self, site=None, level=None, module=None, searchKey=None):
        params = {}

        if level is not None:
            if level not in ValidLevelFilters:
                raise TypeError("invalid level filter")
            params["filters.level"] = level

        if module is not None:
            if module not in ValidModuleFilters:
                raise TypeError("invalid module filter")
            params["filters.module"] = module

        if searchKey is not None:
            params["searchKey"] = searchKey

        return self._geterator(f"/sites/{self.__findKey(site)}/events", params=params)

    ##
    ## Returns the notification settings for given site.
    ##
    def getSiteNotifications(self, site=None):
        return self._get(f"/sites/{self.__findKey(site)}/notification")

    ##
    ## Returns the list of settings for the given site.
    ##
    def getSiteSettings(self, site=None):
        return self._get(f"/sites/{self.__findKey(site)}/setting")

    ##
    ## Push back the settings for the site.
    ##
    def setSiteSettings(self, settings, site=None):
        return self.__patch(f"/sites/{self.__findKey(site)}/setting", json=settings)

    ##
    ## Returns the list of timerange profiles for the given site.
    ##
    def getTimeRanges(self, site=None):
        return self._get(f"/sites/{self.__findKey(site)}/setting/profiles/timeranges")

    ##
    ## Returns the list of wireless network groups.
    ##
    ## This is the "WLAN Group" list on Settings > Wireless Networks.
    ##
    def getWirelessGroups(self, site=None):
        return self._get(f"/sites/{self.__findKey(site)}/setting/wlans")

    ##
    ## Returns the list of wireless networks for the given group.
    ##
    ## This is the main SSID list on Settings > Wireless Networks.
    ##
    def getWirelessNetworks(self, group, site=None):
        return self._get(f"/sites/{self.__findKey(site)}/setting/wlans/{group}/ssids")
