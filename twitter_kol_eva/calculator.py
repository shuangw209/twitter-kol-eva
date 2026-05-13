"""The 6 metric formulas, kept pure and dependency-free.

Formulas (matches the user spec):
    ER          = (likes + comments + shares) / followers
    View ER     = (likes + comments + shares) / avg_views
    C/L Ratio   = comments / likes
    Reach Rate  = avg_views / followers
    Stability   = max_views / min_views
    CPM         = price / (avg_views / 1000)

Edge cases:
    * Any divide-by-zero returns 0.0 and adds a note to the report.
    * Stability is clamped to >= 1.0 (when only one sample, returns 1.0).
    * Negative inputs are treated as 0.
"""

from __future__ import annotations

from statistics import mean

from twitter_kol_eva.models import Metrics, Report, Sample


def _safe_div(num: float, denom: float) -> float:
    if denom == 0:
        return 0.0
    return num / denom


def calculate_metrics(
    *,
    handle: str,
    profile_url: str,
    followers: int,
    samples: list[Sample],
    price: float,
    currency: str = "USD",
) -> Report:
    """Build a Report from raw samples.

    `samples` should be a list of original tweets (retweets excluded by the
    scraper, but this function does not assume that).
    """

    notes: list[str] = []

    # Sanitize counts
    clean: list[Sample] = []
    for s in samples:
        clean.append(
            Sample(
                tweet_id=s.tweet_id,
                url=s.url,
                posted_at=s.posted_at,
                views=max(0, s.views),
                likes=max(0, s.likes),
                comments=max(0, s.comments),
                shares=max(0, s.shares),
            )
        )

    sample_size = len(clean)
    if sample_size == 0:
        notes.append("No samples available — every metric will be 0.")
    elif sample_size < 3:
        notes.append(
            f"Only {sample_size} sample(s). Metrics may be noisy; aim for ≥ 5 for "
            "a meaningful read."
        )

    if followers <= 0:
        notes.append("Followers count is 0 or unknown — ER and Reach Rate will be 0.")

    # Aggregates
    avg_views = mean(s.views for s in clean) if clean else 0.0
    avg_likes = mean(s.likes for s in clean) if clean else 0.0
    avg_comments = mean(s.comments for s in clean) if clean else 0.0
    avg_shares = mean(s.shares for s in clean) if clean else 0.0
    total_engagement_avg = avg_likes + avg_comments + avg_shares

    # Stability uses min/max views across samples; ignore zero-view samples
    # (those are usually parsing failures, not real zero-impression tweets).
    nonzero_views = [s.views for s in clean if s.views > 0]
    if len(nonzero_views) >= 2:
        stability = max(nonzero_views) / min(nonzero_views)
    elif len(nonzero_views) == 1:
        stability = 1.0
        notes.append(
            "Only one sample had a non-zero view count — stability set to 1.0 "
            "but is not meaningful."
        )
    else:
        stability = 0.0
        notes.append(
            "No samples had a non-zero view count. View ER, Reach Rate, "
            "Stability, and CPM will be 0. Did the scraper hit a login wall?"
        )

    if avg_views == 0:
        notes.append(
            "Average views is 0 — View ER / Reach Rate / CPM are not meaningful."
        )

    if avg_likes == 0:
        notes.append("Average likes is 0 — C/L Ratio set to 0.")

    metrics = Metrics(
        er=_safe_div(total_engagement_avg, followers),
        view_er=_safe_div(total_engagement_avg, avg_views),
        cl_ratio=_safe_div(avg_comments, avg_likes),
        reach_rate=_safe_div(avg_views, followers),
        stability=stability,
        cpm=_safe_div(price, avg_views / 1000.0) if avg_views > 0 else 0.0,
    )

    return Report(
        handle=handle,
        profile_url=profile_url,
        followers=followers,
        price=price,
        currency=currency,
        sample_size=sample_size,
        avg_views=avg_views,
        avg_likes=avg_likes,
        avg_comments=avg_comments,
        avg_shares=avg_shares,
        metrics=metrics,
        samples=clean,
        notes=notes,
    )
