import pytest


@pytest.fixture(autouse=True)
def mock_events_resp(configure_paginated_get, default_api_v2, resources_dir):
    return configure_paginated_get(
        default_api_v2 / "sites" / "0bf476c155ea24942722c5a8b516adfe" / "events",
        resources_dir / "get_site_events.json",
    )


def test_get_site_events(mock_events_resp, active_omada):
    rv = list(active_omada.get_site_events())
    assert mock_events_resp.called
    assert len(rv) == 3372


@pytest.mark.parametrize(
    "kwargs, exp_qs",
    [
        ({}, {}),
        (
            {"time_start": 100, "time_end": 200},
            {"filters.timestart": "100", "filters.timeend": "200"},
        ),
        (
            {"time_start": 42, "module": "System"},
            {"filters.timestart": "42", "filters.module": "system"},
        ),
    ],
)
def test_get_site_events_query_params(mock_events_resp, active_omada, kwargs, exp_qs):
    list(active_omada.get_site_events(**kwargs))
    assert mock_events_resp.called
    ignore_qs_params = {"_", "token", "currentpage", "currentpagesize"}
    for req in mock_events_resp.request_history:
        qs_as_dict = {
            key: val[0] for (key, val) in req.qs.items() if key not in ignore_qs_params
        }
        assert qs_as_dict == exp_qs
