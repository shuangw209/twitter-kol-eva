"""Data classes used across the package.

Sample  — one tweet's raw counts.
Metrics — the 6 computed metrics.
Report  — what the CLI prints / writes to disk.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class Sample:
    """One tweet's raw engagement counts.

    `views` is X's "impression" count shown under each tweet.
    All counts are integers; missing fields default to 0.
    """

    tweet_id: str = ""
    url: str = ""
    posted_at: str = ""  # ISO-8601 string if known, else ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0  # retweets + quotes

    @property
    def total_engagement(self) -> int:
        return self.likes + self.comments + self.shares


@dataclass
class Metrics:
    """The 6 metrics the user asked for.

    All ratios are stored as decimals (0.025 = 2.5%). The CLI formats them
    as percentages where that makes sense.
    """

    er: float = 0.0  # (likes + comments + shares) / followers
    view_er: float = 0.0  # (likes + comments + shares) / avg_views
    cl_ratio: float = 0.0  # comments / likes
    reach_rate: float = 0.0  # avg_views / followers
    stability: float = 0.0  # max_views / min_views
    cpm: float = 0.0  # price / (avg_views / 1000)


@dataclass
class Report:
    """Top-level result. Serializable to JSON via asdict()."""

    handle: str
    profile_url: str
    followers: int
    price: float
    currency: str
    sample_size: int
    avg_views: float
    avg_likes: float
    avg_comments: float
    avg_shares: float
    metrics: Metrics
    samples: list[Sample] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
