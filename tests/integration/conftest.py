"""Test-only host workaround for flaky new connections from Python to studio.genlayer.com.

Observed on Windows: `curl.exe` and a bare `requests.post` reach the RPC in ~2 s, but during a
longer gltest run genlayer-py's `requests` calls intermittently fail with ConnectTimeout (its
timeout is None, so the OS waits ~21 s) after the host has tried an AAAA address with no IPv6
route. This shim (a) resolves IPv4 only and (b) retries *connection* failures, which are safe to
retry because no request bytes were sent. It does not touch the contract or any assertion.
"""
import socket

import requests.adapters
import urllib3.util.connection as _conn
from urllib3.util.retry import Retry

_conn.allowed_gai_family = lambda: socket.AF_INET

_orig_init = requests.adapters.HTTPAdapter.__init__


def _init(self, *args, **kwargs):
    kwargs.setdefault("max_retries", Retry(total=6, connect=6, read=0, backoff_factor=1.5, allowed_methods=None))
    _orig_init(self, *args, **kwargs)


requests.adapters.HTTPAdapter.__init__ = _init
