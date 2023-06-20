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
