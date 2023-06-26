import pytest

import omada


@pytest.mark.parametrize("code", [42, "42", 42.0])
def test_good(code):
    err = omada.OmadaError({"errorCode": code, "msg": "hello"})
    assert str(err) == "Omada error: self.code=42, self.msg='hello'"
    assert err.code == 42
    assert err.msg == "hello"


def test_missing_code():
    err = omada.OmadaError({"msg": "test"})
    assert err.code == 99_999
    assert err.msg == "\n".join(
        [
            "Error extracting error code: KeyError('errorCode')",
            "test",
        ]
    )


def test_missing_message():
    err = omada.OmadaError({"errorCode": 12})
    assert err.code == 12
    assert err.msg == "\n".join(
        [
            "Error extracting error message: KeyError('msg')",
            "Input json: {'errorCode': 12}",
        ]
    )


def test_input_str():
    err = omada.OmadaError("EVERYTHING IS BROKEN")
    assert err.code == 99_999
    try:
        "a string"["a key"]
    except TypeError as type_error:
        sub_err = type_error
    assert err.msg == "\n".join(
        [
            f"Error extracting error code: {sub_err!r}",
            f"Error extracting error message: {sub_err!r}",
            "Input json: 'EVERYTHING IS BROKEN'",
        ]
    )


def test_input_none():
    err = omada.OmadaError(None)
    assert err.code == 99_999
    assert err.msg == "\n".join(
        [
            """Error extracting error code: TypeError("'NoneType' object is not subscriptable")""",
            """Error extracting error message: TypeError("'NoneType' object is not subscriptable")""",
            "Input json: None",
        ]
    )


def test_input_int():
    err = omada.OmadaError(12)
    assert err.code == 99_999
    assert err.msg == "\n".join(
        [
            """Error extracting error code: TypeError("'int' object is not subscriptable")""",
            """Error extracting error message: TypeError("'int' object is not subscriptable")""",
            "Input json: 12",
        ]
    )
