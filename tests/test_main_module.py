import pytest
import yarl

import omada


def test_module():
    assert omada


@pytest.fixture
def test_config():
    return omada.OmadaConfig(
        base_url=yarl.URL(R"https://euw1-api-omada-controller.tplinkcloud.com"),
        omada_controller_id="04b2f7c62fb249ca993a113df25aaa27",
        site="Default",
    )


@pytest.fixture
def test_omada(test_config, requests_mock):
    out = omada.Omada(test_config)
    out.login_result = omada.api_bindings.LoginResult(
        omadacId="424242", roleType=42, token="mytoken"
    )
    return out


@pytest.fixture
def default_api_v2():
    return yarl.URL(
        "https://euw1-api-omada-controller.tplinkcloud.com/04b2f7c62fb249ca993a113df25aaa27/api/v2"
    )


def test_config_obj(test_config, test_omada):
    assert test_omada.config == test_config


def test_login(test_config, requests_mock, resources_dir):
    requests_mock.post(
        "https://euw1-api-omada-controller.tplinkcloud.com/04b2f7c62fb249ca993a113df25aaa27/api/v2/login",
        text=(resources_dir / "login_result.json").open().read(),
    )
    result = omada.Omada(test_config).login("hello", "world")

    assert requests_mock.call_count == 1
    assert result.token == "b7184f03caa34e7a8f786bd8f5295219"


@pytest.mark.freeze_time("2023-01-01")
def test_logout(test_omada, requests_mock):
    assert test_omada.login_result is not None

    requests_mock.post(
        "https://euw1-api-omada-controller.tplinkcloud.com/04b2f7c62fb249ca993a113df25aaa27/api/v2/logout?token=mytoken&_=1672531200000",
        text="""{"errorCode":0,"msg":"Success."}""",
    )
    rv = test_omada.logout()

    assert test_omada.login_result is None
    assert rv is True


@pytest.mark.freeze_time("2023-01-01")
def test_current_user(resources_dir, test_omada, default_api_v2, requests_mock):
    assert test_omada.login_result is not None

    requests_mock.get(
        str(default_api_v2 / "users" / "current"),
        text=(resources_dir / "current_user.json").open().read(),
    )
    rv = test_omada.get_current_user()

    assert rv.email == "hello@example.com"
