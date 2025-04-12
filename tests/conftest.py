from pathlib import Path
import pytest
import responses
from bs4 import BeautifulSoup

mocking = True

HERE = Path(__file__).parent
MOCKED_URLS = {
    "example": [("https://example.com", Path(HERE / "example.html").read_text())],
    "httpbin": [
        ("http://httpbin.org/links/2/0", Path(HERE / "links20.html").read_text()),
        ("http://httpbin.org/links/2/1", Path(HERE / "links21.html").read_text()),

    ],
}


def mocker(item):
    with responses.RequestsMock() as rsp:
        for key, value in MOCKED_URLS[item]:
            print(f"*** ADDED {key} for mocking")
            rsp.add(responses.GET, key, body=value, status=200)

        yield MOCKED_URLS[item]


@pytest.fixture
def mocked_example():
    yield from mocker("example")


@pytest.fixture
def mocked_httpbin():
    yield from mocker("httpbin")


@pytest.fixture
def BS():
    return BeautifulSoup

