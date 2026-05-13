"""Tests for the metric formulas — pure logic, no network."""

import math

import pytest

from twitter_kol_eva.calculator import calculate_metrics
from twitter_kol_eva.models import Sample


def make_samples(specs):
    """specs: list of (views, likes, comments, shares)."""
    return [
        Sample(
            tweet_id=str(i),
            url=f"https://x.com/x/status/{i}",
            views=v,
            likes=l,
            comments=c,
            shares=s,
        )
        for i, (v, l, c, s) in enumerate(specs)
    ]


def test_basic_metrics():
    # 3 tweets, all identical: 10000 views, 100 likes, 20 comments, 5 shares
    samples = make_samples([(10000, 100, 20, 5)] * 3)
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=10_000,
        samples=samples,
        price=500,
        currency="USD",
    )

    # avg views = 10000, avg engagement = 125
    assert r.sample_size == 3
    assert r.avg_views == 10000
    # ER = 125/10000 = 0.0125
    assert math.isclose(r.metrics.er, 0.0125, rel_tol=1e-6)
    # View ER = 125/10000 = 0.0125
    assert math.isclose(r.metrics.view_er, 0.0125, rel_tol=1e-6)
    # C/L = 20/100 = 0.2
    assert math.isclose(r.metrics.cl_ratio, 0.2, rel_tol=1e-6)
    # Reach = 10000/10000 = 1.0
    assert math.isclose(r.metrics.reach_rate, 1.0, rel_tol=1e-6)
    # Stability = 10000/10000 = 1.0
    assert math.isclose(r.metrics.stability, 1.0, rel_tol=1e-6)
    # CPM = 500 / (10000/1000) = 50
    assert math.isclose(r.metrics.cpm, 50.0, rel_tol=1e-6)


def test_zero_followers_gives_zero_er():
    samples = make_samples([(1000, 10, 1, 1)] * 3)
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=0,
        samples=samples,
        price=100,
    )
    assert r.metrics.er == 0.0
    assert r.metrics.reach_rate == 0.0
    assert any("Followers count is 0" in n for n in r.notes)


def test_zero_views_gives_zero_view_er_and_cpm():
    samples = make_samples([(0, 10, 2, 1)] * 3)
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=1000,
        samples=samples,
        price=100,
    )
    assert r.metrics.view_er == 0.0
    assert r.metrics.cpm == 0.0
    assert r.metrics.reach_rate == 0.0
    # ER still works (uses follower denominator)
    assert math.isclose(r.metrics.er, 13 / 1000, rel_tol=1e-6)


def test_zero_likes_gives_zero_cl_ratio():
    samples = make_samples([(1000, 0, 5, 1)] * 3)
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=1000,
        samples=samples,
        price=100,
    )
    assert r.metrics.cl_ratio == 0.0
    assert any("C/L Ratio set to 0" in n for n in r.notes)


def test_stability_uses_min_max_views():
    samples = make_samples(
        [
            (1000, 10, 1, 1),
            (5000, 50, 5, 5),
            (10000, 100, 10, 10),
        ]
    )
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=10_000,
        samples=samples,
        price=200,
    )
    # Stability = 10000 / 1000 = 10.0
    assert math.isclose(r.metrics.stability, 10.0, rel_tol=1e-6)


def test_stability_ignores_zero_view_samples():
    samples = make_samples(
        [
            (0, 5, 1, 0),  # parsing failure — should be ignored for stability
            (2000, 20, 2, 2),
            (4000, 40, 4, 4),
        ]
    )
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=10_000,
        samples=samples,
        price=200,
    )
    # Stability = 4000 / 2000 = 2.0 (zero-view sample skipped)
    assert math.isclose(r.metrics.stability, 2.0, rel_tol=1e-6)


def test_empty_samples_returns_zero_metrics_and_notes():
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=1000,
        samples=[],
        price=100,
    )
    assert r.sample_size == 0
    assert r.metrics.er == 0.0
    assert r.metrics.cpm == 0.0
    assert any("No samples available" in n for n in r.notes)


def test_low_sample_warning():
    samples = make_samples([(1000, 10, 1, 1)])
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=1000,
        samples=samples,
        price=100,
    )
    assert any("noisy" in n for n in r.notes)


def test_negative_inputs_clamped_to_zero():
    samples = [Sample(tweet_id="1", views=-100, likes=-5, comments=-1, shares=-1)]
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=1000,
        samples=samples,
        price=100,
    )
    assert r.avg_views == 0
    assert r.avg_likes == 0
    assert r.metrics.er == 0.0


def test_cpm_calculation():
    # 1 tweet, 50000 views, price 250 -> CPM = 250 / 50 = 5
    samples = make_samples([(50000, 100, 10, 5)])
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=100_000,
        samples=samples,
        price=250,
    )
    assert math.isclose(r.metrics.cpm, 5.0, rel_tol=1e-6)


def test_to_dict_roundtrip():
    """Report.to_dict() should be JSON-serializable and contain all metric keys."""
    import json

    samples = make_samples([(1000, 10, 1, 1)] * 3)
    r = calculate_metrics(
        handle="x",
        profile_url="https://x.com/x",
        followers=10_000,
        samples=samples,
        price=100,
    )
    d = r.to_dict()
    s = json.dumps(d)  # must not raise
    parsed = json.loads(s)
    assert "metrics" in parsed
    for k in ("er", "view_er", "cl_ratio", "reach_rate", "stability", "cpm"):
        assert k in parsed["metrics"]
