"""SSRF-safety tests for the URL guard and the REST API remote-backend gate.

Covers CVE-class CWE-918: the unauthenticated ``/humanize`` endpoint must
not let a client coerce the server into fetching internal/loopback URLs.

URL-literal targets are used throughout so the tests never perform real DNS
lookups or network I/O (``getaddrinfo`` short-circuits numeric literals).
"""

from __future__ import annotations

import urllib.request

import pytest

from texthumanize._urlguard import safe_urlopen, validate_outbound_url
from texthumanize.exceptions import UnsafeURLError

# ── URL guard: unsafe targets are rejected ────────────────────

@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9000/",             # loopback (the PoC target)
        "http://127.0.0.1/",
        "http://localhost.localdomain",       # resolves via literal path only
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://10.0.0.1/",                   # RFC1918
        "http://192.168.1.1/admin",           # RFC1918
        "http://172.16.5.4/",                 # RFC1918
        "http://[::1]/",                      # IPv6 loopback
        "http://[::ffff:127.0.0.1]/",         # IPv4-mapped loopback
        "http://0.0.0.0/",                    # unspecified
    ],
)
def test_rejects_internal_targets(url):
    with pytest.raises(UnsafeURLError):
        validate_outbound_url(url)


def test_rejects_metadata_ip_specifically():
    with pytest.raises(UnsafeURLError) as exc:
        validate_outbound_url("http://169.254.169.254/")
    assert "link-local" in str(exc.value)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/",                 # disallowed scheme
        "file:///etc/passwd",                 # disallowed scheme
        "gopher://127.0.0.1/",                # disallowed scheme
        "",                                   # empty
        "   ",                                # blank
        "http://",                            # no host
        "http://user:pass@93.184.216.34/",    # embedded credentials
    ],
)
def test_rejects_malformed_or_disallowed(url):
    with pytest.raises(UnsafeURLError):
        validate_outbound_url(url)


# ── URL guard: legitimate public targets pass ─────────────────

@pytest.mark.parametrize(
    "url",
    [
        "https://93.184.216.34/",             # public IPv4 literal
        "http://93.184.216.34:8080/api/chat",
        "https://[2606:2800:220:1:248:1893:25c8:1946]/",  # public IPv6 literal
    ],
)
def test_allows_public_targets(url):
    assert validate_outbound_url(url) == url


def test_loopback_opt_in_for_trusted_callers():
    # Trusted in-process callers (e.g. a local Ollama) may opt in.
    assert (
        validate_outbound_url("http://127.0.0.1:11434/", allow_loopback=True)
        == "http://127.0.0.1:11434/"
    )


def test_private_opt_in_for_trusted_callers():
    assert (
        validate_outbound_url("http://10.0.0.5:8000/", allow_private=True)
        == "http://10.0.0.5:8000/"
    )


# ── REST API: remote backends gated off by default ───────────

@pytest.fixture
def no_remote(monkeypatch):
    monkeypatch.delenv("TEXTHUMANIZE_API_ALLOW_REMOTE_BACKENDS", raising=False)


@pytest.fixture
def remote_allowed(monkeypatch):
    monkeypatch.setenv("TEXTHUMANIZE_API_ALLOW_REMOTE_BACKENDS", "1")


@pytest.mark.usefixtures("no_remote")
def test_local_humanize_needs_no_gate():
    from texthumanize.api import _handle_humanize

    result = _handle_humanize({"text": "A short test sentence here.", "lang": "en"})
    assert "text" in result


@pytest.mark.usefixtures("no_remote")
def test_oss_api_url_blocked_by_default():
    from texthumanize.api import RemoteBackendDisabled, _handle_humanize

    with pytest.raises(RemoteBackendDisabled):
        _handle_humanize(
            {
                "text": "hello world here",
                "lang": "en",
                "backend": "oss",
                "oss_api_url": "http://127.0.0.1:9000",
            }
        )


@pytest.mark.usefixtures("no_remote")
def test_remote_backend_name_blocked_by_default():
    from texthumanize.api import RemoteBackendDisabled, _handle_humanize

    with pytest.raises(RemoteBackendDisabled):
        _handle_humanize({"text": "hello world", "lang": "en", "backend": "openai"})


@pytest.mark.usefixtures("remote_allowed")
def test_ssrf_url_rejected_even_when_remote_enabled():
    from texthumanize.api import _handle_humanize

    with pytest.raises(UnsafeURLError):
        _handle_humanize(
            {
                "text": "hello world here",
                "lang": "en",
                "backend": "oss",
                "oss_api_url": "http://169.254.169.254/latest/meta-data/",
            }
        )


@pytest.mark.usefixtures("remote_allowed")
def test_public_url_accepted_when_remote_enabled():
    # backend stays 'local', so no real network call — validates the URL
    # passes the guard and the request completes.
    from texthumanize.api import _handle_humanize

    result = _handle_humanize(
        {
            "text": "A short test sentence here.",
            "lang": "en",
            "oss_api_url": "https://93.184.216.34/",
        }
    )
    assert "text" in result


# ── safe_urlopen: validation + response-size cap ──────────────

def test_safe_urlopen_rejects_unsafe_before_connecting():
    # Metadata IP must be refused before any socket is opened.
    with pytest.raises(UnsafeURLError):
        safe_urlopen("http://169.254.169.254/", timeout=1.0)


def test_safe_urlopen_rejects_unsafe_request_object():
    req = urllib.request.Request("http://127.0.0.1:9000/", method="GET")
    with pytest.raises(UnsafeURLError):
        safe_urlopen(req, timeout=1.0)


def test_safe_urlopen_metadata_blocked_even_with_allow_flags():
    # allow_loopback/allow_private must NOT re-enable link-local metadata.
    with pytest.raises(UnsafeURLError):
        safe_urlopen(
            "http://169.254.169.254/",
            timeout=1.0,
            allow_loopback=True,
            allow_private=True,
        )


def test_safe_urlopen_caps_response(monkeypatch):
    # Stub urlopen so no real network is used; assert the size cap fires.
    class _FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def read(self, n):
            return self._payload[:n]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    import texthumanize._urlguard as guard

    monkeypatch.setattr(
        guard.urllib.request, "urlopen",
        lambda request, timeout: _FakeResp(b"x" * 100),
    )
    # Public literal passes validation; body (100 B) exceeds max_bytes=10.
    with pytest.raises(ValueError):
        safe_urlopen("https://93.184.216.34/", timeout=1.0, max_bytes=10)


def test_default_bind_host_is_loopback():
    import inspect

    from texthumanize.api import create_app, run_server

    assert inspect.signature(create_app).parameters["host"].default == "127.0.0.1"
    assert inspect.signature(run_server).parameters["host"].default == "127.0.0.1"
