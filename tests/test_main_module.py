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
    assert rv == [
        omada.api_bindings.SiteGroup(
            count=1,
            groupId="c940f920b66440eabac81a24498b8e2a",
            name="IPGroup_Any",
            type=0,
            buildIn=False,
            site="951ecc287ba5437b946ede8d0fb40339",
            ipList=[{"ip": "0.0.0.0", "mask": 0}],
        ),
        omada.api_bindings.SiteGroup(
            count=1,
            groupId="BI-IPv6Group_Any",
            name="IPv6Group_Any",
            type=3,
            buildIn=True,
            ipv6List=[{"ip": "::", "prefix": 0}],
        ),
        omada.api_bindings.SiteGroup(
            count=1,
            groupId="b657569c820d43feb46fd0b4c91ba6dd",
            name="Custom Potato site group",
            type=0,
            buildIn=False,
            site="951ecc287ba5437b946ede8d0fb40339",
            ipList=[{"ip": "192.168.7.1", "mask": 24}],
        ),
    ]


def test_get_portal_candidates(
    resources_dir,
    default_api_v2,
    requests_mock,
    active_omada,
):
    requests_mock.get(
        str(
            default_api_v2
            / "sites"
            / "324af3bf9c4a49e6ae68d2513fc296bd"
            / "setting"
            / "portal"
            / "candidates"
        ),
        text=(resources_dir / "get_portal_candidates.json").open().read(),
    )
    rv = active_omada.get_portal_candidates()
    assert rv == omada.api_bindings.PortalCandidates(
        networkList=[
            omada.api_bindings.NamedObject(
                id="b71fb66cefe04bb8bccdb3dee83f2e24", name="LAN"
            )
        ],
        wlanList=[
            omada.api_bindings.WlanList(
                wlanId="7a83fd1000de4acb8614efa7d5772411",
                wlanName="Default",
                ssidList=[
                    omada.api_bindings.NamedObject(
                        id="bb775c93c4e948a3b52ca70e869d6e5f", name="TEST SSID1"
                    ),
                    omada.api_bindings.NamedObject(
                        id="56e0d9f324c24581a4f54bf8a3b8f316", name="TEST SSID2"
                    ),
                    omada.api_bindings.NamedObject(
                        id="cd72e1c878024a589b63c3a039f33b85", name="TEST SSID3"
                    ),
                    omada.api_bindings.NamedObject(
                        id="913f3956aedd4e78b4cc5a0c5982f037", name="TEST SSID4"
                    ),
                ],
            )
        ],
    )


def test_get_scenarios(requests_mock, default_api_v2, resources_dir, active_omada):
    requests_mock.get(
        str(default_api_v2 / "scenarios"),
        text=(resources_dir / "get_scenarios.json").open().read(),
    )
    rv = active_omada.get_scenarios()
    assert rv == [
        "Hotel",
        "Restaurant",
        "Shopping Mall",
        "Airport",
        "Office",
        "Factory",
        "Dormitory",
        "Campus",
        "Hospital",
        "Home",
    ]


def test_get_sites(
    requests_mock, default_api_v2, resources_dir, active_omada, default_omada_params
):
    params = default_omada_params.copy()
    params.update({"currentPage": 1, "currentPageSize": 10})
    requests_mock.get(
        str((default_api_v2 / "sites") % params),
        text=(resources_dir / "get_sites.json").open().read(),
    )
    rv = list(active_omada.get_sites())
    assert rv == [
        omada.api_bindings.Site(
            id="d1b689274df0434493b1c566ec5950cc",
            name="Default",
            wlanGuestNum=1,
            wirelessUpgrade=False,
            type=0,
            region="United Kingdom",
            unplaced=False,
            primary=True,
            wlanDeviceIsolatedNum=0,
            wan=True,
            wlan=True,
            wlanDeviceConnectedNum=3,
            wlanUserNum=18,
            lanDeviceConnectedNum=0,
            scenario="Office",
            lan=False,
            lanDeviceDisconnectedNum=0,
            wiredUpgrade=False,
            timeZone="UTC",
            wlanDeviceDisconnectedNum=0,
            lanUserNum=5,
            deviceAccount={"password": "user-pass", "username": "user@example.com"},
        )
    ]


def test_get_site_devices(requests_mock, default_api_v2, resources_dir, active_omada):
    requests_mock.get(
        str(default_api_v2 / "sites" / "324af3bf9c4a49e6ae68d2513fc296bd" / "devices"),
        text=(resources_dir / "get_site_devices.json").open().read(),
    )
    rv = list(active_omada.get_site_devices())
    assert len(rv) == 4
