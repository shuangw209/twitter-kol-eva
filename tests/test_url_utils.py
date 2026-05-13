"""Tests for handle/URL parsing."""

import pytest

from twitter_kol_eva.url_utils import parse_handle, profile_url


@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("elonmusk", "elonmusk"),
        ("@elonmusk", "elonmusk"),
        ("https://twitter.com/elonmusk", "elonmusk"),
        ("https://x.com/elonmusk", "elonmusk"),
        ("https://www.x.com/elonmusk/", "elonmusk"),
        ("twitter.com/elonmusk?lang=en", "elonmusk"),
        ("https://x.com/elonmusk/status/1234567890", "elonmusk"),
        ("https://mobile.twitter.com/elonmusk", "elonmusk"),
        ("X_AE_A_12", "X_AE_A_12"),  # 9 chars + numbers + underscore is fine
    ],
)
def test_parse_handle_valid(input_str, expected):
    assert parse_handle(input_str) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "https://facebook.com/elonmusk",
        "https://x.com/",
        "this has spaces",
        "@",
        "thisHandleIsWayTooLongForTwitter",  # > 15 chars
    ],
)
def test_parse_handle_invalid(bad):
    with pytest.raises(ValueError):
        parse_handle(bad)


def test_profile_url():
    assert profile_url("elonmusk") == "https://x.com/elonmusk"
