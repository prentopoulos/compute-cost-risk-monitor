"""Tests run offline: pytest-socket blocks network sockets for every test.

The address below is TEST-NET-1 (RFC 5737), reserved for documentation, so even a
broken guard would reach no real service.
"""

import socket
import urllib.request

import pytest
from pytest_socket import SocketBlockedError

# pytest-socket warns as it raises; the raise is what these tests check.
pytestmark = pytest.mark.filterwarnings("ignore:A test tried to use socket")


def test_network_socket_is_blocked() -> None:
    with pytest.raises(SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def test_http_request_is_blocked() -> None:
    with pytest.raises(SocketBlockedError):
        urllib.request.urlopen("http://192.0.2.1/", timeout=1)  # noqa: S310
