"""Decide whether a forwarding header may be trusted.

Forwarded IP and protocol headers are set by reverse proxies, but any direct
client can invent them. Trust is determined by the address of the peer that
opened the connection, against an explicit operator-configured allowlist.

This module has no dependency on the app or settings objects so both the rate
limiter and the owner cookie can share one definition of trust without a
circular import.
"""

from __future__ import annotations

import ipaddress
import logging

logger = logging.getLogger("dreamai.web")


def peer_is_trusted(peer: str, trusted_proxies: tuple[str, ...]) -> bool:
    """Whether ``peer`` matches a configured proxy address or CIDR range."""
    if not peer or not trusted_proxies:
        return False
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for entry in trusted_proxies:
        try:
            if address in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            logger.warning("invalid trusted proxy entry: %s", entry)
    return False


def forwarded_ip(
    peer: str, headers: dict[str, str], trusted_proxies: tuple[str, ...]
) -> str | None:
    """The client IP from headers, only when the peer is a trusted proxy."""
    if not peer_is_trusted(peer, trusted_proxies):
        return None
    real = headers.get("x-real-ip")
    if real:
        return real.strip()
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return None


def forwarded_proto(
    peer: str, headers: dict[str, str], trusted_proxies: tuple[str, ...]
) -> str | None:
    """The forwarded scheme, only when the peer is a trusted proxy."""
    if not peer_is_trusted(peer, trusted_proxies):
        return None
    return headers.get("x-forwarded-proto")
