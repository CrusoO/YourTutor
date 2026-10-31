"""Which address is the client: X-Forwarded-For counts only from a trusted proxy."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app import proxy
from app.config import Settings, production_secret_errors, settings
from app.proxy import resolve_client_ip, trusted_networks

NETS = trusted_networks("127.0.0.1, 10.0.0.0/8, fd00::/8")


def _request(peer: str | None, *forwarded: str) -> Request:
    headers = [(b"x-forwarded-for", line.encode()) for line in forwarded]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "client": (peer, 5000) if peer else None,
    }
    return Request(scope)


def test_with_no_trusted_proxy_the_header_is_ignored() -> None:
    assert resolve_client_ip("203.0.113.9", ["198.51.100.7"], trusted_networks("")) == "203.0.113.9"
    assert resolve_client_ip("127.0.0.1", ["198.51.100.7"], trusted_networks("")) == "127.0.0.1"


def test_a_header_from_an_untrusted_address_is_ignored() -> None:
    assert resolve_client_ip("203.0.113.9", ["198.51.100.7"], NETS) == "203.0.113.9"
    assert resolve_client_ip("203.0.113.9", ["10.1.1.1"], NETS) == "203.0.113.9"  # spoofed "inside"


def test_a_trusted_proxy_is_believed() -> None:
    assert resolve_client_ip("127.0.0.1", ["198.51.100.7"], NETS) == "198.51.100.7"
    assert resolve_client_ip("127.0.0.1", [], NETS) == "127.0.0.1"  # no header: the proxy itself


def test_with_several_hops_the_first_untrusted_address_from_the_right_is_used() -> None:
    chain = ["203.0.113.50, 198.51.100.7, 10.2.3.4"]  # the first entry was made up by the client
    assert resolve_client_ip("127.0.0.1", chain, NETS) == "198.51.100.7"
    assert resolve_client_ip("10.9.9.9", ["198.51.100.7", "10.2.3.4"], NETS) == "198.51.100.7"
    assert resolve_client_ip("127.0.0.1", ["10.1.1.1, 10.2.2.2"], NETS) == "10.1.1.1"  # all trusted


def test_cidr_ranges_ipv6_and_mapped_addresses_match() -> None:
    assert resolve_client_ip("10.255.0.1", ["198.51.100.7"], NETS) == "198.51.100.7"
    assert resolve_client_ip("11.0.0.1", ["198.51.100.7"], NETS) == "11.0.0.1"
    assert resolve_client_ip("fd12::1", ["2001:db8::5"], NETS) == "2001:db8::5"
    assert resolve_client_ip("::ffff:127.0.0.1", ["198.51.100.7"], NETS) == "198.51.100.7"


def test_a_header_we_cannot_read_never_chooses_the_address() -> None:
    assert resolve_client_ip("127.0.0.1", ["not-an-ip"], NETS) == "127.0.0.1"
    assert resolve_client_ip("127.0.0.1", ["198.51.100.7, junk"], NETS) == "127.0.0.1"
    assert resolve_client_ip("testclient", ["198.51.100.7"], NETS) == "testclient"


def test_several_header_lines_count_as_one_chain() -> None:
    request = _request("127.0.0.1", "203.0.113.50", "198.51.100.7")
    settings.trusted_proxies = "127.0.0.1"
    assert proxy.client_ip(request) == "198.51.100.7"


def test_a_bad_setting_is_reported_as_an_error() -> None:
    with pytest.raises(ValueError):
        trusted_networks("10.0.0.0/8, banana")


def test_a_request_without_a_peer_is_unknown() -> None:
    settings.trusted_proxies = ""
    assert proxy.client_ip(_request(None)) == "unknown"


def test_an_ignored_header_from_this_machine_is_remembered_once() -> None:
    proxy.reset_ignored_header()
    settings.trusted_proxies = ""
    proxy.note_ignored_header(_request("203.0.113.9", "198.51.100.7"))  # a stranger: not a proxy
    assert not proxy.header_ignored_from_loopback()
    proxy.note_ignored_header(_request("127.0.0.1"))  # no header
    assert not proxy.header_ignored_from_loopback()
    proxy.note_ignored_header(_request("127.0.0.1", "198.51.100.7"))
    assert proxy.header_ignored_from_loopback()
    proxy.reset_ignored_header()
    settings.trusted_proxies = "127.0.0.1"  # configured: nothing to warn about
    proxy.note_ignored_header(_request("127.0.0.1", "198.51.100.7"))
    assert not proxy.header_ignored_from_loopback()


def test_production_refuses_the_default_database_password() -> None:
    prod = Settings(app_env="production", postgres_password="tutor")
    assert production_secret_errors(prod) == ["POSTGRES_PASSWORD"]
    assert (
        production_secret_errors(Settings(app_env="production", postgres_password="x" * 20)) == []
    )
    assert (
        production_secret_errors(Settings(app_env="development", postgres_password="tutor")) == []
    )
