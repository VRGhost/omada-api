import pydantic


class LoginResult(pydantic.BaseModel, extra=pydantic.Extra.allow):
    omadacId: str
    roleType: int
    token: str
