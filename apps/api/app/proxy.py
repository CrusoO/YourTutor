"""Which address is the client? X-Forwarded-For is believed only when a trusted proxy sent it.

`TRUSTED_PROXIES` is a comma-separated list of addresses or CIDR ranges (for example `127.0.0.1` or
`10.0.0.0/8`). Empty, the default, means the header is ignored and the connecting address is used.
Anyone who can reach the API directly could otherwise send a made-up address and escape the rate
limits.
"""

from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache

from fastapi import Request

from app.config import settings

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

logger = logging.getLogger("yourtutor.access")
_ignored = {"header_seen_from_loopback": False}


@lru_cache(maxsize=8)
def _parse(raw: str) -> tuple[IPNetwork, ...]:
    return tuple(
        ipaddress.ip_network(part.strip(), strict=False) for part in raw.split(",") if part.strip()
    )


def trusted_networks(raw: str | None = None) -> tuple[IPNetwork, ...]:
    """The configured proxies; a bad entry raises ValueError (checked at startup)."""
    return _parse(settings.trusted_proxies if raw is None else raw)


def _address(text: str) -> IPAddress | None:
    try:
        addr = ipaddress.ip_address(text.strip())
    except ValueError:
        return None
    mapped = getattr(addr, "ipv4_mapped", None)
    return mapped if mapped is not None else addr


def _is_trusted(addr: IPAddress, networks: tuple[IPNetwork, ...]) -> bool:
    return any(addr in network for network in networks)


def resolve_client_ip(
    peer: str, forwarded_lines: list[str], networks: tuple[IPNetwork, ...]
) -> str:
    """The connecting address, unless a trusted proxy connected: then the first untrusted hop
    counting from the right of X-Forwarded-For (the leftmost hop if every hop is trusted)."""
    if not networks:
        return peer
    peer_addr = _address(peer)
    if peer_addr is None or not _is_trusted(peer_addr, networks):
        return peer
    hops = [hop.strip() for line in forwarded_lines for hop in line.split(",") if hop.strip()]
    parsed = [_address(hop) for hop in hops]
    if not parsed or any(addr is None for addr in parsed):
        return peer  # no header, or one we cannot read: never let it pick the bucket
    for addr in reversed(parsed):
        assert addr is not None
        if not _is_trusted(addr, networks):
            return str(addr)
    return str(parsed[0])


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    return resolve_client_ip(peer, request.headers.getlist("x-forwarded-for"), trusted_networks())


def note_ignored_header(request: Request) -> None:
    """Remember (and log once) that a request from this machine carried X-Forwarded-For while no
    proxy is trusted: that is a proxy in front of the API with TRUSTED_PROXIES not set."""
    if (
        trusted_networks()
        or "x-forwarded-for" not in request.headers
        or _ignored["header_seen_from_loopback"]
    ):
        return
    peer = _address(request.client.host) if request.client else None
    if peer is not None and peer.is_loopback:
        _ignored["header_seen_from_loopback"] = True
        logger.warning(
            "X-Forwarded-For arrived from this machine but TRUSTED_PROXIES is empty: every visitor "
            "shares one rate-limit address. Set TRUSTED_PROXIES=127.0.0.1 behind a local proxy."
        )


def header_ignored_from_loopback() -> bool:
    return _ignored["header_seen_from_loopback"]


def reset_ignored_header() -> None:
    _ignored["header_seen_from_loopback"] = False
