"""Shared HTTP helper used by every collector."""
import time
import requests

import config

_session = requests.Session()
_session.headers.update({"User-Agent": config.USER_AGENT})


def get(url, params=None, headers=None, retries=2, timeout=None):
    """GET with polite retries. Returns a requests.Response or raises on final failure."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = _session.get(
                url, params=params, headers=headers,
                timeout=timeout or config.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            return resp
        except Exception as exc:  # noqa: BLE001 - collectors must never crash the run
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    raise last_exc
