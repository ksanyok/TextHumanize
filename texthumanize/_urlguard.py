"""SSRF-safety validation for outbound URLs (stdlib-only).

TextHumanize can be pointed at user-supplied HTTP endpoints (e.g. the
OSS Gradio backend via ``oss_api_url``). When such a URL originates from
an untrusted source — most importantly the network-facing REST API — it
must be validated before the library performs an outbound request, or an
attacker can coerce the server into reaching internal services
(Server-Side Request Forgery, CWE-918).

:func:`validate_outbound_url` parses the URL, enforces an http/https
scheme, resolves *every* address the hostname maps to, and rejects the
request if any resolved address is loopback, private, link-local
(including the ``169.254.169.254`` cloud-metadata endpoint), reserved,
multicast, or otherwise non-public.

Trusted, in-process callers that intentionally target localhost (for
example a developer pointing the Ollama backend at
``http://localhost:11434``) can opt out via ``allow_loopback`` /
``allow_private``. The REST API never opts out.

Note on DNS rebinding: validation resolves the name at check time. A host
that resolves to a public address here but a private one at connection
time (DNS rebinding) is not caught by name-based validation alone. The
REST API mitigates this primarily by keeping remote backends disabled by
default; pinning the validated IP through the HTTP connection is tracked
as future hardening.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.request
from typing import Union
from urllib.parse import urlsplit

from texthumanize.exceptions import UnsafeURLError

__all__ = ["validate_outbound_url", "is_safe_public_ip", "safe_urlopen"]

_ALLOWED_SCHEMES = frozenset({"http", "https"})

# Default cap on how much of an outbound response we will read into memory.
_DEFAULT_MAX_RESPONSE_BYTES = 10_000_000  # 10 MB


def is_safe_public_ip(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    allow_loopback: bool = False,
    allow_private: bool = False,
) -> bool:
    """Return True if *ip* is a routable public address.

    Unwraps IPv4-mapped IPv6 addresses (``::ffff:a.b.c.d``) so that an
    attacker cannot smuggle a private IPv4 target inside an IPv6 literal.
    """
    # Unwrap IPv4-mapped / 6to4-style IPv6 so the underlying v4 address
    # is subject to the same checks.
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None:
            ip = mapped

    # Always-block categories are checked FIRST. In Python 3.12+ these ranges
    # (notably link-local 169.254.0.0/16) also report ``is_private``/``is_loopback``,
    # so checking the allow-flag categories first would let ``allow_private`` /
    # ``allow_loopback`` wrongly re-enable the cloud-metadata endpoint.
    if (
        ip.is_link_local      # 169.254.0.0/16 incl. 169.254.169.254 metadata
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False
    if ip.is_loopback:
        return bool(allow_loopback)
    if ip.is_private:
        # is_private covers RFC1918, unique-local (fc00::/7), etc.
        return bool(allow_private)
    return True


def validate_outbound_url(
    url: str,
    *,
    allow_loopback: bool = False,
    allow_private: bool = False,
) -> str:
    """Validate that *url* is safe to fetch, returning it unchanged.

    Args:
        url: The URL to validate.
        allow_loopback: Permit loopback targets (127.0.0.0/8, ::1).
            Only for trusted in-process callers.
        allow_private: Permit RFC1918 / unique-local targets. Only for
            trusted in-process callers.

    Returns:
        The original URL string if it passes validation.

    Raises:
        UnsafeURLError: If the URL is malformed, uses a disallowed
            scheme, embeds credentials, or resolves to a non-public
            address.
    """
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError(str(url), "empty or non-string URL")

    parts = urlsplit(url.strip())

    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeURLError(
            url, f"scheme {parts.scheme!r} not in {sorted(_ALLOWED_SCHEMES)}"
        )

    # Reject embedded credentials (user:pass@host) — an exfil/confusion vector.
    if parts.username or parts.password:
        raise UnsafeURLError(url, "embedded credentials are not allowed")

    host = parts.hostname
    if not host:
        raise UnsafeURLError(url, "missing hostname")

    port = parts.port  # may raise ValueError on a bad port literal
    if port is not None and not (0 < port < 65536):
        raise UnsafeURLError(url, f"invalid port {port}")

    # Resolve the hostname to every address it maps to and check each one.
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(url, f"hostname does not resolve ({exc})") from exc

    if not infos:
        raise UnsafeURLError(url, "hostname resolved to no addresses")

    for family, _type, _proto, _canon, sockaddr in infos:
        addr = sockaddr[0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError as exc:
            raise UnsafeURLError(url, f"unparseable address {addr!r}") from exc
        if not is_safe_public_ip(
            ip, allow_loopback=allow_loopback, allow_private=allow_private
        ):
            raise UnsafeURLError(
                url,
                f"resolves to non-public address {ip} "
                f"(category: {_ip_category(ip)})",
            )

    return url


def safe_urlopen(
    request: Union[urllib.request.Request, str],
    *,
    timeout: float,
    max_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
    allow_loopback: bool = False,
    allow_private: bool = False,
) -> bytes:
    """Validate a request's URL, open it, and read at most ``max_bytes``.

    A single choke point for the library's outbound HTTP: it re-validates
    the effective URL with :func:`validate_outbound_url` immediately before
    the request and bounds the response size so a hostile or oversized body
    cannot exhaust memory (or be reflected wholesale).

    Args:
        request: A :class:`urllib.request.Request` or a URL string.
        timeout: Socket timeout in seconds (required — never unbounded).
        max_bytes: Maximum number of response bytes to read.
        allow_loopback: Permit loopback targets (trusted callers only).
        allow_private: Permit private targets (trusted callers only).

    Returns:
        The response body, truncated to ``max_bytes`` at most.

    Raises:
        UnsafeURLError: If the URL fails SSRF validation.
        ValueError: If the response exceeds ``max_bytes``.
    """
    url = request.full_url if isinstance(request, urllib.request.Request) else str(request)
    # Re-validate right before dispatch (link-local/metadata, multicast and
    # reserved are rejected even when loopback/private are explicitly allowed).
    validate_outbound_url(
        url, allow_loopback=allow_loopback, allow_private=allow_private
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:  # nosec B310 — URL validated above
        body: bytes = resp.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError(
            f"outbound response exceeded {max_bytes} bytes and was rejected"
        )
    return body


def _ip_category(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    """Human-readable classification for error messages."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    # Mirror the precedence in is_safe_public_ip: always-block first.
    if ip.is_link_local:
        return "link-local"
    if ip.is_multicast:
        return "multicast"
    if ip.is_reserved:
        return "reserved"
    if ip.is_unspecified:
        return "unspecified"
    if ip.is_loopback:
        return "loopback"
    if ip.is_private:
        return "private"
    return "other-non-public"
