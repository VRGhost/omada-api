import dataclasses
import enum
import functools
import http.client
import logging
import typing
from datetime import datetime

import requests
import urllib3
import yarl
from requests.cookies import RequestsCookieJar

from . import api_bindings

logger = logging.getLogger(__name__)


def timestamp() -> int:
    """Omada API calls expects timestamp in milliseconds."""
    return int(datetime.utcnow().timestamp() * 1000)


class OmadaError(Exception):
    """Display errorCode and optional message returned from Omada API."""

    def __init__(self, json):
        self.errorCode = 0
        self.msg = None

        if json is None:
            raise TypeError("json cannot be None")

        if "errorCode" in json:
            self.errorCode = int(json["errorCode"])

        if "msg" in json:
            self.msg = '"' + json["msg"] + '"'

    def __str__(self):
        return f"errorCode={self.errorCode}, msg={self.msg}"


##
## Group types
##
@enum.unique
class GroupType(enum.Enum):
    IPGroup = 0  # "IP Group"
    IPPortGroup = 1  # "IP-Port Group"
    MACGroup = 2  # "MAC Group"


##
## Alert and event levels
##
@enum.unique
class LevelFilter(enum.Enum):
    Error = 0
    Warning = 1
    Information = 2


##
## Alert and event modules
##
@enum.unique
class ModuleFilter(enum.Enum):
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
    warnings: bool = True
    verbose: bool = False


class Omada:
    """The main Omada API class."""

    ##
    ## Initialize a new Omada API instance.
    ##
    def __init__(self, config: OmadaConfig):
        self.config = config
        # self.login_result = None
        # self.currentUser = {}
        # self.apiPath = Omada.ApiPath
        # self.omadacId = ""

        # set up requests session and cookies
        self.session = requests.Session()
        self.session.cookies = RequestsCookieJar()
        self.session.verify = self.config.ssl_verify

        # hide warnings about insecure SSL requests
        if not self.config.ssl_verify and not self.warnings:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # enable verbose output
        if self.config.verbose:
            # set debug level in http.client
            http.client.HTTPConnection.debuglevel = 1
            # initialize logger
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            # configure logging for requests
            logger.setLevel(logging.DEBUG)
            logger.propagate = True

    @functools.cached_property
    def omada_controller_id(self) -> str:
        if self.config.omada_controller_id:
            out = self.config.omada_controller_id
        else:
            raise NotImplementedError(
                "TODO: implement fetch from self.baseurl + '/api/info' when talking to the controller locally"
            )
        return out

    @property
    def api_root(self) -> yarl.URL:
        return self.config.base_url / self.omada_controller_id / "api" / "v2"

    def _default_request_params(self) -> dict:
        return {"_": timestamp(), "token": self.login_result.token}

    def get_json_response(self, response) -> dict:
        """Post-processing of a generic omada api request"""
        response.raise_for_status()
        json = response.json()
        if json.get("errorCode") == 0:
            return json.get("result", None)
        raise OmadaError(json)

    ##
    ## Look up a site key given the name.
    ##
    def __findKey(self, name=None):
        # Use the stored site if not provided.
        if name is None:
            name = self.site

        # Look for the site in the privilege list.
        for site in self.currentUser["privilege"]["sites"]:
            if site["name"] == name:
                return site["key"]

        raise PermissionError(f'current user does not have privilege to site "{name}"')

    def __get(self, path):
        """Perform a GET request and return the result."""
        if self.login_result is None:
            raise ConnectionError("not logged in")

        response = self.session.get(
            self.api_root / path,
            headers=self.session.headers,
        )
        return self.get_json_response(response)

    ##
    ## Perform a PATCH request and return the result.
    ##
    def __patch(self, path, params={}, data=None, json=None):
        if self.login_result is None:
            raise ConnectionError("not logged in")

        if not isinstance(params, dict):
            raise TypeError("params must be a dictionary")

        params["_"] = timestamp()
        params["token"] = self.login_result["token"]

        response = self.session.patch(
            self.__buildUrl(path), params=params, data=data, json=json
        )
        response.raise_for_status()

        json = response.json()
        if json["errorCode"] == 0:
            return json["result"] if "result" in json else None

        raise OmadaError(json)

    ##
    ## Return True if a result contains data.
    ##
    def __hasData(self, result):
        return (result is not None) and ("data" in result) and (len(result["data"]) > 0)

    ##
    ## Perform a paged GET request and return the result.
    ##
    def __getPaged(self, path, params={}, data=None, json=None):
        if self.login_result is None:
            raise ConnectionError("not logged in")

        if not isinstance(params, dict):
            raise TypeError("params must be a dictionary")

        params["_"] = timestamp()
        params["token"] = self.login_result["token"]

        params.setdefault("currentPage", 1)
        params.setdefault("currentPageSize", 10)

        response = self.session.get(
            self.__buildUrl(path), params=params, data=data, json=json
        )
        response.raise_for_status()

        json = response.json()
        if json["errorCode"] == 0:
            json["result"]["path"] = path
            json["result"]["params"] = params
            return json["result"]

        raise OmadaError(json)

    ##
    ## Returns the next page of data if more is available.
    ##
    def __nextPage(self, result):
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
        return self.__getPaged(path, params)

    ##
    ## Perform a GET request and yield the results.
    ##
    def __geterator(self, path, params={}, data=None, json=None):
        result = self.__getPaged(path, params, data, json)
        while self.__hasData(result):
            for item in result["data"]:
                yield item
            result = self.__nextPage(result)

    login_result: api_bindings.LoginResult = None

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

            # Get the current user info.
            # self.currentUser = self.getCurrentUser()

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

    ##
    ## Returns the current login status.
    ##
    def getLoginStatus(self):
        return self.__get("/loginStatus")

    def get_current_user(self):
        """Returns the current user information."""
        return api_bindings.CurrentUser(**self.__get("users/current"))

    ##
    ## Returns the list of groups for the given site.
    ##
    def getSiteGroups(self, site=None, type=None):
        return self.__get(
            f"/sites/{self.__findKey(site)}/setting/profiles/groups"
            + (f"/{type}" if type else "")
        )

    ##
    ## Returns the list of portal candidates for the given site.
    ##
    ## This is the "SSID & Network" list on Settings > Authentication > Portal > Basic Info.
    ##
    def getPortalCandidates(self, site=None):
        return self.__get(f"/sites/{self.__findKey(site)}/setting/portal/candidates")

    ##
    ## Returns the list of RADIUS profiles for the given site.
    ##
    def getRadiusProfiles(self, site=None):
        return self.__get(f"/sites/{self.__findKey(site)}/setting/radiusProfiles")

    ##
    ## Returns the list of scenarios.
    ##
    def getScenarios(self):
        return self.__get("/scenarios")

    ##
    ## Returns the list of all sites.
    ##
    def getSites(self):
        return self.__geterator("/sites")

    ##
    ## Returns the list of devices for given site.
    ##
    def getSiteDevices(self, site=None):
        return self.__get(f"/sites/{self.__findKey(site)}/devices")

    ##
    ## Returns the list of active clients for given site.
    ##
    def getSiteClients(self, site=None):
        return self.__geterator(
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

        return self.__geterator(f"/sites/{self.__findKey(site)}/alerts", params=params)

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

        return self.__geterator(f"/sites/{self.__findKey(site)}/events", params=params)

    ##
    ## Returns the notification settings for given site.
    ##
    def getSiteNotifications(self, site=None):
        return self.__get(f"/sites/{self.__findKey(site)}/notification")

    ##
    ## Returns the list of settings for the given site.
    ##
    def getSiteSettings(self, site=None):
        return self.__get(f"/sites/{self.__findKey(site)}/setting")

    ##
    ## Push back the settings for the site.
    ##
    def setSiteSettings(self, settings, site=None):
        return self.__patch(f"/sites/{self.__findKey(site)}/setting", json=settings)

    ##
    ## Returns the list of timerange profiles for the given site.
    ##
    def getTimeRanges(self, site=None):
        return self.__get(f"/sites/{self.__findKey(site)}/setting/profiles/timeranges")

    ##
    ## Returns the list of wireless network groups.
    ##
    ## This is the "WLAN Group" list on Settings > Wireless Networks.
    ##
    def getWirelessGroups(self, site=None):
        return self.__get(f"/sites/{self.__findKey(site)}/setting/wlans")

    ##
    ## Returns the list of wireless networks for the given group.
    ##
    ## This is the main SSID list on Settings > Wireless Networks.
    ##
    def getWirelessNetworks(self, group, site=None):
        return self.__get(f"/sites/{self.__findKey(site)}/setting/wlans/{group}/ssids")
