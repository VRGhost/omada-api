import json
import pathlib
import typing

import pytest
import yarl

import omada


@pytest.fixture
def resources_dir():
    return pathlib.Path(__file__).parent.resolve() / "resources"


@pytest.fixture
def test_config():
    return omada.OmadaConfig(
        base_url=yarl.URL(R"https://euw1-api-omada-controller.tplinkcloud.com"),
        omada_controller_id="04b2f7c62fb249ca993a113df25aaa27",
        site="obf-word misty tyrant",
    )


@pytest.fixture
def login_result_dict(resources_dir):
    return json.load((resources_dir / "login_result.json").open())


@pytest.fixture
def default_api_v2():
    return yarl.URL(
        "https://euw1-api-omada-controller.tplinkcloud.com/04b2f7c62fb249ca993a113df25aaa27/api/v2"
    )


@pytest.fixture
def default_omada_params(freezer, login_result_dict):
    """Default omada request params"""
    freezer.move_to("2023-01-01")
    ts = 1672531200000  # 2023-01-01 utcnow
    return {"_": ts, "token": login_result_dict["result"]["token"]}


@pytest.fixture
def inactive_omada(
    login_result_dict, requests_mock, test_config, default_api_v2, resources_dir
):
    out = omada.Omada(test_config)
    requests_mock.post(
        str(default_api_v2 / "login"),
        text=json.dumps(login_result_dict),
    )
    requests_mock.get(
        str(default_api_v2 / "users" / "current"),
        text=(resources_dir / "current_user.json").open().read(),
    )
    requests_mock.get(
        str(default_api_v2 / "loginStatus"),
        text='{"errorCode":0,"msg":"Success.","result":{"login":true}}',
    )
    return out


@pytest.fixture
def active_omada(requests_mock, inactive_omada):
    inactive_omada.login("testuser", "testpass")
    requests_mock.reset_mock()
    return inactive_omada


@pytest.fixture
def configure_paginated_get(requests_mock):
    # A binding to configure paginated get (_geterator)
    def _configure_fn_impl(
        url: typing.Union[str, yarl.URL],
        data: typing.Union[pathlib.Path, typing.Iterable[dict]],
    ):
        if isinstance(data, pathlib.Path):
            with data.open() as fin:
                pages = json.load(fin)
        elif isinstance(data, (list, tuple)):
            pages = data
        else:
            raise NotImplementedError(data)

        def _get_page_cb(request, response) -> str:
            try:
                current_page = request.qs["currentpage"][0]
            except (KeyError, IndexError):
                current_page = "1"
            current_page = int(current_page)
            # current page index starts with one, not zero
            return json.dumps(pages[current_page - 1])

        binding = requests_mock.get(str(url), text=_get_page_cb)
        return binding

    return _configure_fn_impl
