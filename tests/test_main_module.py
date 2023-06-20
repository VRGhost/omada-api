import pytest

import omada


def test_module():
    assert omada


def test_config_obj(test_config, inactive_omada):
    assert inactive_omada.config == test_config


def inactive_omada(test_config, requests_mock):
    result = inactive_omada.login("hello", "world")

    assert requests_mock.call_count == 1
    assert result.token == "b7184f03caa34e7a8f786bd8f5295219"


def test_logout(active_omada, requests_mock, default_api_v2, default_omada_params):
    assert active_omada.login_result is not None
    requests_mock.post(
        str(default_api_v2 / "logout" % default_omada_params),
        text="""{"errorCode":0,"msg":"Success."}""",
    )
    rv = active_omada.logout()

    assert active_omada.login_result is None
    assert rv is True


def test_current_user(active_omada, requests_mock):
    assert active_omada.login_result is not None

    rv = active_omada.get_current_user()

    assert rv.email == "hello@example.com"
    # Check the attribute too
    assert active_omada.current_user == rv
    assert requests_mock.call_count == 2

    rv2 = active_omada.get_current_user()
    assert rv2.email == "hello@example.com"
    assert requests_mock.call_count == 3


def test_current_user_attribute(active_omada, requests_mock):
    assert active_omada.login_result is not None

    rv1 = active_omada.current_user
    assert rv1.email == "hello@example.com"
    # Check the attribute too
    assert active_omada.current_user == rv1
    assert requests_mock.call_count == 1

    rv2 = active_omada.current_user
    assert rv2.email == "hello@example.com"
    # Check the attribute too
    assert active_omada.current_user == rv2
    assert requests_mock.call_count == 1

    assert rv1 is rv2


class TestRequestCalls:
    def test_get(self, requests_mock, default_api_v2, active_omada):
        matcher = requests_mock.get(
            str(default_api_v2 / "hello" / "get"),
            text="""{"errorCode":0,"result":"TEST PASSED."}""",
        )
        rv = active_omada._get("hello/get")
        assert rv == "TEST PASSED."
        assert (
            matcher.last_request.headers["Csrf-Token"]
            == "b7184f03caa34e7a8f786bd8f5295219"
        )

    def test_patch(
        self, requests_mock, default_api_v2, active_omada, default_omada_params
    ):
        matcher = requests_mock.patch(
            str(default_api_v2 / "hello" / "patch" % default_omada_params),
            text="""{"errorCode":0,"result":"TEST PASSED."}""",
        )
        rv = active_omada._patch("hello/patch")
        assert rv == "TEST PASSED."
        assert (
            matcher.last_request.headers["Csrf-Token"]
            == "b7184f03caa34e7a8f786bd8f5295219"
        )


class TestFindSite:
    def test_default(self, active_omada):
        x = active_omada._find_site()
        assert x == "324af3bf9c4a49e6ae68d2513fc296bd"

    @pytest.mark.parametrize(
        "inp, exp_out",
        [
            ("Default", "324af3bf9c4a49e6ae68d2513fc296bd"),
            ("MyTestSite", "MyTestSiteKey"),
        ],
    )
    def test_explicit_pass(self, active_omada, inp, exp_out):
        assert active_omada._find_site(inp) == exp_out

    def test_missing_fetch(self, active_omada):
        with pytest.raises(omada.OmadaError) as err:
            active_omada._find_site("idontexist")

        assert err.value.code == 99001
        assert (
            err.value.msg == 'Current user does not have privilege to site "idontexist"'
        )


def test_login_statis(requests_mock, active_omada):
    rv = active_omada.get_login_status()
    assert rv is True
    assert requests_mock.call_count == 1


@pytest.mark.parametrize(
    "site_name, expected_site_id",
    [
        (None, "324af3bf9c4a49e6ae68d2513fc296bd"),
        ("Default", "324af3bf9c4a49e6ae68d2513fc296bd"),
        ("MyTestSite", "MyTestSiteKey"),
    ],
)
@pytest.mark.parametrize(
    "type_str, exp_type_url", [(None, None), ("", None), ("test_type", "test_type")]
)
def test_get_default_site_groups(
    resources_dir,
    default_api_v2,
    requests_mock,
    active_omada,
    site_name,
    expected_site_id,
    type_str,
    exp_type_url,
):
    requests_mock.get(
        str(
            default_api_v2
            / "sites"
            / expected_site_id
            / "setting"
            / "profiles"
            / "groups"
            / (exp_type_url or "")
        ),
        text=(resources_dir / "get_site_groups.json").open().read(),
    )
    rv = active_omada.get_site_groups(site_name, type_str)
    # assert rv == 1
