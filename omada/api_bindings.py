# ruff: noqa: N815, A003
import typing

import pydantic


class LoginResult(pydantic.BaseModel, extra=pydantic.Extra.allow):
    omadacId: str
    roleType: int
    token: str


class Site(pydantic.BaseModel, extra=pydantic.Extra.allow):
    name: str
    category: str
    key: str


class UserPrivilege(pydantic.BaseModel, extra=pydantic.Extra.allow):
    all: bool
    sites: typing.List[Site]


class CurrentUser(pydantic.BaseModel, extra=pydantic.Extra.allow):
    name: str
    email: str
    privilege: UserPrivilege


class SiteGroup(pydantic.BaseModel, extra=pydantic.Extra.allow):
    count: int
    groupId: str
    name: str
    type: int

    buildIn: bool = False


class NamedObject(pydantic.BaseModel, extra=pydantic.Extra.allow):
    id: str
    name: str


class WlanList(pydantic.BaseModel, extra=pydantic.Extra.allow):
    wlanId: str
    wlanName: str
    ssidList: typing.List[NamedObject]


class PortalCandidates(pydantic.BaseModel, extra=pydantic.Extra.allow):
    networkList: typing.List[NamedObject]
    wlanList: typing.List[WlanList]


class Site(NamedObject):
    pass


class Device(pydantic.BaseModel, extra=pydantic.Extra.allow):
    active: bool
    site: str
    sn: str
