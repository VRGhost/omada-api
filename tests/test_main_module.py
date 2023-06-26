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

    assert rv["email"] == "obf-word@objective@cynicism"
    # Check the attribute too
    assert active_omada.current_user == rv
    assert requests_mock.call_count == 2

    rv2 = active_omada.get_current_user()
    assert rv2["email"] == "obf-word@objective@cynicism"
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
        {
            "count": 1,
            "groupId": "0bf4f1e21b27bccf86b22c13a65ca73e",
            "ipList": [{"ip": "0.0.0.0", "mask": 0}],
            "name": "obf-word vivacious notification",
            "site": "0bf45529b28ae3fbfd9c961c383a532c",
            "type": 0,
        },
        {
            "buildIn": True,
            "count": 1,
            "groupId": "BI-IPv6Group_Any",
            "ipv6List": [{"ip": "::", "prefix": 0}],
            "name": "obf-word average advertising",
            "type": 3,
        },
        {
            "count": 1,
            "groupId": "0bf492e3890eec3fdc3dfd46e4f4c253",
            "ipList": [{"ip": "192.168.7.1", "mask": 24}],
            "name": "obf-word bad duchess",
            "site": "0bf45529b28ae3fbfd9c961c383a532c",
            "type": 0,
        },
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
    assert rv == {
        "networkList": [
            {
                "id": "0bf463694d5bd772d67fc7056dd2d52b",
                "name": "obf-word applicable fixing",
            }
        ],
        "wlanList": [
            {
                "ssidList": [
                    {
                        "id": "0bf4ac8c4927d7f73f7b467a90702b6c",
                        "name": "obf-word terrible university",
                    },
                    {
                        "id": "0bf4550903431138b882276593942dfd",
                        "name": "obf-word calm opposition",
                    },
                    {
                        "id": "0bf4540ae01bbb5793cba85b4f0f2a6f",
                        "name": "obf-word unfortunate balls",
                    },
                    {
                        "id": "0bf4bfdf37630c9ae82908983bdf25d8",
                        "name": "obf-word exciting lineup",
                    },
                ],
                "wlanId": "0bf4cf91fd4e537312645de572441ff9",
                "wlanName": "obf-word misty tyrant",
            }
        ],
    }


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
    params.update({"currentPage": 1, "currentPageSize": 100})
    requests_mock.get(
        str((default_api_v2 / "sites") % params),
        text=(resources_dir / "get_sites.json").open().read(),
    )
    rv = list(active_omada.get_sites())
    assert rv == [
        {
            "deviceAccount": {
                "password": "obf-word steep advice",
                "username": "obf-word@annual@chemotherapy",
            },
            "id": "0bf49e3a75cab962401cc44f058ecffa",
            "lan": False,
            "lanDeviceConnectedNum": 0,
            "lanDeviceDisconnectedNum": 0,
            "lanUserNum": 5,
            "name": "obf-word misty tyrant",
            "primary": True,
            "region": "United Kingdom",
            "scenario": "Office",
            "timeZone": "UTC",
            "type": 0,
            "unplaced": False,
            "wan": True,
            "wiredUpgrade": False,
            "wirelessUpgrade": False,
            "wlan": True,
            "wlanDeviceConnectedNum": 3,
            "wlanDeviceDisconnectedNum": 0,
            "wlanDeviceIsolatedNum": 0,
            "wlanGuestNum": 1,
            "wlanUserNum": 18,
        }
    ]


def test_get_site_devices(requests_mock, default_api_v2, resources_dir, active_omada):
    requests_mock.get(
        str(default_api_v2 / "sites" / "0bf476c155ea24942722c5a8b516adfe" / "devices"),
        text=(resources_dir / "get_site_devices.json").open().read(),
    )
    rv = list(active_omada.get_site_devices())
    assert len(rv) == 4


def configure_iter_get(requests_mock, source_file, url):
    with source_file.open() as fin:
        responses = json.load(fin)
    # This is a multi-page responmse
    for idx, response in enumerate(responses):
        requests_mock.get(
            str(url % {"currentPage": idx + 1}),
            text=json.dumps(response),
        )
    return responses


def test_get_site_clients(requests_mock, default_api_v2, resources_dir, active_omada):
    configure_iter_get(
        requests_mock,
        resources_dir / "get_site_clients.json",
        default_api_v2 / "sites" / "0bf476c155ea24942722c5a8b516adfe" / "clients",
    )

    rv = list(active_omada.get_site_clients())
    assert len(rv) == 32


def test_get_site_alerts(requests_mock, default_api_v2, resources_dir, active_omada):
    configure_iter_get(
        requests_mock,
        resources_dir / "get_site_alerts.json",
        default_api_v2 / "sites" / "0bf476c155ea24942722c5a8b516adfe" / "clients",
    )

    rv = list(active_omada.get_site_clients())
    assert len(rv) == 30


def test_get_site_events(requests_mock, default_api_v2, resources_dir, active_omada):
    configure_iter_get(
        requests_mock,
        resources_dir / "get_site_events.json",
        default_api_v2 / "sites" / "0bf476c155ea24942722c5a8b516adfe" / "events",
    )

    rv = list(active_omada.get_site_events())
    assert len(rv) == 3372


def test_get_site_notifications(
    requests_mock, default_api_v2, resources_dir, active_omada
):
    requests_mock.get(
        str(
            default_api_v2
            / "sites"
            / "0bf476c155ea24942722c5a8b516adfe"
            / "notification"
        ),
        text=(resources_dir / "get_site_notifications.json").open().read(),
    )

    rv = list(active_omada.get_site_notifications())
    assert len(rv) == 2


def test_get_site_settings(requests_mock, default_api_v2, resources_dir, active_omada):
    requests_mock.get(
        str(default_api_v2 / "sites" / "0bf476c155ea24942722c5a8b516adfe" / "setting"),
        text=(resources_dir / "get_site_settings.json").open().read(),
    )

    rv = active_omada.get_site_settings()
    assert rv == {
        "advancedFeature": {"enable": True},
        "airtimeFairness": {"enable2g": True, "enable5g": True, "enable6g": True},
        "alert": {"delay": 60, "delayEnable": True, "enable": False},
        "autoUpgrade": {"enable": False},
        "bandSteering": {
            "connectionThreshold": 30,
            "differenceThreshold": 4,
            "enable": False,
            "maxFailures": 5,
        },
        "bandSteeringForMultiBand": {"mode": 0},
        "beaconControl": {
            "beaconInterval2g": 100,
            "beaconInterval5g": 100,
            "beaconInterval6g": 100,
            "dtimPeriod2g": 1,
            "dtimPeriod5g": 1,
            "dtimPeriod6g": 1,
            "fragmentationThreshold2g": 2346,
            "fragmentationThreshold5g": 2346,
            "fragmentationThreshold6g": 2346,
            "rtsThreshold2g": 2347,
            "rtsThreshold5g": 2347,
            "rtsThreshold6g": 2347,
        },
        "channelLimit": {"enable": False},
        "deviceAccount": {
            "password": "obf-word maximum dugout",
            "username": "obf-word@dry@counselor",
        },
        "led": {"enable": True},
        "lldp": {"enable": False},
        "mesh": {
            "autoFailoverEnable": True,
            "defGatewayEnable": True,
            "fullSector": True,
            "meshEnable": False,
        },
        "remoteLog": {"enable": False, "moreClientLog": False, "port": 514},
        "roaming": {
            "aiRoamingEnable": True,
            "dualBand11kReportEnable": False,
            "fastRoamingEnable": True,
            "forceDisassociationEnable": True,
        },
        "site": {
            "dst": {
                "enable": False,
                "end": {},
                "endTime": 0,
                "lastEnd": 0,
                "lastStart": 0,
                "nextEnd": 0,
                "nextStart": 0,
                "start": {},
                "startTime": 0,
                "status": False,
            },
            "key": "0bf439c052feea54d4ed841ee52396b0",
            "mapToken": "pk-eyJ1IjoidHBsaW5rIiwiYSI6ImNsaXXXXXXXXXXXX3eXzY3MyDnQzN2huYnoifQ.hmshbHDzJ_6bDMTMspjs8w",
            "name": "obf-word misty tyrant",
            "ntpEnable": False,
            "ntpServers": [],
            "omadacId": "0bf4a53bce14114e1d38ede8f999b687",
            "primary": True,
            "region": "United Kingdom",
            "scenario": "Office",
            "timeZone": "UTC",
            "type": 0,
            "unplaced": True,
            "useGlobalMapToken": True,
        },
        "speedTest": {"enable": False, "interval": 120},
    }


def test_set_site_settings(
    default_omada_params, requests_mock, default_api_v2, active_omada
):
    matcher = requests_mock.patch(
        str(
            (default_api_v2 / "sites" / "0bf476c155ea24942722c5a8b516adfe" / "setting")
            % default_omada_params
        ),
        text="""{"errorCode":0,"msg":"Success."}""",
    )

    rv = active_omada.set_site_settings(settings={"hello": "world"})
    assert matcher.last_request.json() == {"hello": "world"}
    assert rv is True


def test_get_time_ranges(requests_mock, default_api_v2, active_omada):
    requests_mock.get(
        str(
            default_api_v2
            / "sites"
            / "0bf476c155ea24942722c5a8b516adfe"
            / "setting"
            / "profiles"
            / "timeranges"
        ),
        text="""{"errorCode":0,"msg":"Success.","result":{"data":["I have no example here"]}}""",
    )

    rv = active_omada.get_time_ranges()
    assert rv == ["I have no example here"]


def test_get_wireless_groups(
    requests_mock, default_api_v2, resources_dir, active_omada
):
    requests_mock.get(
        str(
            default_api_v2
            / "sites"
            / "0bf476c155ea24942722c5a8b516adfe"
            / "setting"
            / "wlans"
        ),
        text=(resources_dir / "get_settings_wlans.json").open().read(),
    )

    rv = active_omada.get_wireless_groups()
    assert rv == [
        {
            "clone": False,
            "id": "0bf411d007bfcb720159226fc8e047a9",
            "name": "obf-word misty tyrant",
            "primary": True,
            "site": "0bf439c052feea54d4ed841ee52396b0",
        }
    ]


def test_get_wireless_networks(
    requests_mock, default_api_v2, resources_dir, active_omada
):
    requests_mock.get(
        str(
            default_api_v2
            / "sites"
            / "0bf476c155ea24942722c5a8b516adfe"
            / "setting"
            / "wlans"
            / "HELLO_WORLD"
            / "ssids"
        ),
        text=(resources_dir / "get_wireless_networks.json").open().read(),
    )

    rv = list(active_omada.get_wireless_networks(group_id="HELLO_WORLD"))
    assert len(rv) == 4
