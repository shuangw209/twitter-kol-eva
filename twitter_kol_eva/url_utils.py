"""Parse different forms of Twitter/X handle inputs into a canonical handle.

Accepted inputs:
    elonmusk
    @elonmusk
    https://twitter.com/elonmusk
    https://x.com/elonmusk
    https://x.com/elonmusk/status/123456...   (status URL — handle is still extracted)
    twitter.com/elonmusk?lang=en               (no scheme, with query)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")


def parse_handle(input_str: str) -> str:
    """Return the bare handle (no `@`, no URL).

    Raises ValueError if the input cannot be parsed into a valid handle.
    """
    if not input_str or not input_str.strip():
        raise ValueError("Empty input. Pass a handle or URL like @elonmusk or https://x.com/elonmusk.")

    s = input_str.strip()

    # Bare handle
    if s.startswith("@"):
        s = s[1:]
    if "/" not in s and _HANDLE_RE.match(s):
        return s

    # URL — possibly missing scheme
    if "://" not in s:
        s = "https://" + s
    parsed = urlparse(s)
    host = (parsed.netloc or "").lower()
    if host not in {"twitter.com", "www.twitter.com", "x.com", "www.x.com", "mobile.twitter.com"}:
        raise ValueError(
            f"Not a Twitter/X URL: {input_str!r}. "
            "Expected a handle (e.g. @elonmusk) or a twitter.com / x.com URL."
        )

    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        raise ValueError(f"No handle found in URL: {input_str!r}.")

    candidate = parts[0].lstrip("@")
    if not _HANDLE_RE.match(candidate):
        raise ValueError(
            f"Invalid handle {candidate!r} extracted from {input_str!r}. "
            "Twitter handles are 1–15 chars: letters, digits, underscore."
        )
    return candidate


def profile_url(handle: str) -> str:
    return f"https://x.com/{handle}"
