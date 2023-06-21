import json

import pytest

import omada


def test_module():
    assert omada


def test_config_obj(test_config, inactive_omada):
    assert inactive_omada.config == test_config


def inactive_omada(test_config, requests_mock):
    result = inactive_omada.login("hello", "world")

    assert requests_mock.call_count == 1
    assert result.token == "0bf44cdfeb4609a7f0556872775c0e02"


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

    assert rv.email == "obf-word@objective@cynicism"
    # Check the attribute too
    assert active_omada.current_user == rv
    assert requests_mock.call_count == 2

    rv2 = active_omada.get_current_user()
    assert rv2.email == "obf-word@objective@cynicism"
    assert requests_mock.call_count == 3


def test_current_user_attribute(active_omada, requests_mock):
    assert active_omada.login_result is not None

    rv1 = active_omada.current_user
    assert rv1.email == "obf-word@objective@cynicism"
    # Check the attribute too
    assert active_omada.current_user == rv1
    assert requests_mock.call_count == 1

    rv2 = active_omada.current_user
    assert rv2.email == "obf-word@objective@cynicism"
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
            == "0bf44cdfeb4609a7f0556872775c0e02"
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
            == "0bf44cdfeb4609a7f0556872775c0e02"
        )


class TestFindSite:
    def test_default(self, active_omada):
        x = active_omada._find_site()
        assert x == "0bf476c155ea24942722c5a8b516adfe"

    @pytest.mark.parametrize(
        "inp, exp_out",
        [
            ("obf-word misty tyrant", "0bf476c155ea24942722c5a8b516adfe"),
            ("obf-word old commenter", "MyTestSiteKey"),
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
        (None, "0bf476c155ea24942722c5a8b516adfe"),
        ("obf-word misty tyrant", "0bf476c155ea24942722c5a8b516adfe"),
        ("obf-word old commenter", "MyTestSiteKey"),
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
            groupId="0bf4f1e21b27bccf86b22c13a65ca73e",
            name="obf-word vivacious notification",
            type=0,
            buildIn=False,
            site="0bf45529b28ae3fbfd9c961c383a532c",
            ipList=[{"ip": "0.0.0.0", "mask": 0}],
        ),
        omada.api_bindings.SiteGroup(
            count=1,
            groupId="BI-IPv6Group_Any",
            name="obf-word average advertising",
            type=3,
            buildIn=True,
            ipv6List=[{"ip": "::", "prefix": 0}],
        ),
        omada.api_bindings.SiteGroup(
            count=1,
            groupId="0bf492e3890eec3fdc3dfd46e4f4c253",
            name="obf-word bad duchess",
            type=0,
            buildIn=False,
            site="0bf45529b28ae3fbfd9c961c383a532c",
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
            / "0bf476c155ea24942722c5a8b516adfe"
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
                id="0bf463694d5bd772d67fc7056dd2d52b", name="obf-word applicable fixing"
            )
        ],
        wlanList=[
            omada.api_bindings.WlanList(
                wlanId="0bf4cf91fd4e537312645de572441ff9",
                wlanName="obf-word misty tyrant",
                ssidList=[
                    omada.api_bindings.NamedObject(
                        id="0bf4ac8c4927d7f73f7b467a90702b6c",
                        name="obf-word terrible university",
                    ),
                    omada.api_bindings.NamedObject(
                        id="0bf4550903431138b882276593942dfd",
                        name="obf-word calm opposition",
                    ),
                    omada.api_bindings.NamedObject(
                        id="0bf4540ae01bbb5793cba85b4f0f2a6f",
                        name="obf-word unfortunate balls",
                    ),
                    omada.api_bindings.NamedObject(
                        id="0bf4bfdf37630c9ae82908983bdf25d8",
                        name="obf-word exciting lineup",
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
            id="0bf49e3a75cab962401cc44f058ecffa",
            name="obf-word misty tyrant",
            lan=False,
            type=0,
            wlanDeviceIsolatedNum=0,
            wirelessUpgrade=False,
            wiredUpgrade=False,
            unplaced=False,
            region="United Kingdom",
            wlan=True,
            lanDeviceConnectedNum=0,
            deviceAccount={
                "password": "obf-word steep advice",
                "username": "obf-word@annual@chemotherapy",
            },
            primary=True,
            wlanUserNum=18,
            scenario="Office",
            lanUserNum=5,
            wlanGuestNum=1,
            timeZone="UTC",
            wlanDeviceDisconnectedNum=0,
            lanDeviceDisconnectedNum=0,
            wan=True,
            wlanDeviceConnectedNum=3,
        )
    ]


def test_get_site_devices(requests_mock, default_api_v2, resources_dir, active_omada):
    requests_mock.get(
        str(default_api_v2 / "sites" / "0bf476c155ea24942722c5a8b516adfe" / "devices"),
        text=(resources_dir / "get_site_devices.json").open().read(),
    )
    rv = list(active_omada.get_site_devices())
    assert len(rv) == 4


def test_get_site_clients(requests_mock, default_api_v2, resources_dir, active_omada):
    with (resources_dir / "get_site_clients.json").open() as fin:
        responses = json.load(fin)
    # This is a multi-page responmse
    for idx, response in enumerate(responses):
        requests_mock.get(
            str(
                (
                    default_api_v2
                    / "sites"
                    / "0bf476c155ea24942722c5a8b516adfe"
                    / "clients"
                )
                % {"currentPage": idx + 1}
            ),
            text=json.dumps(response),
        )
    rv = list(active_omada.get_site_clients())
    assert len(rv) == 32
