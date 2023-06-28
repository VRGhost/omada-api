import enum
import typing

import pydantic


@enum.unique
class ModuleFilter(str, enum.Enum):
    """Alert and event modules"""

    Operation = "Operation"
    System = "System"
    Device = "Device"
    Client = "Client"


class SiteEventsInterface(pydantic.BaseModel):
    """Site/events filter"""

    site: typing.Optional[str] = None
    time_start: typing.Optional[int] = None
    time_end: typing.Optional[int] = None
    module: typing.Optional[ModuleFilter] = None
