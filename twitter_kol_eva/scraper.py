"""Twitter/X scraping via Playwright + a saved login cookie file.

Approach (mirrors YoriHan/kol-eval):
    1. Launch headless Chromium with `storage_state` pointing at a JSON cookie
       file the user exported from a logged-in browser session.
    2. Visit https://x.com/<handle>.
    3. Read followers from the profile header.
    4. Scroll the timeline, extract original-tweet stats from rendered DOM.
    5. Skip retweets; cap at `recent_n` tweets.

If Twitter throws up a login wall, we raise TwitterAuthError with guidance.

Why scrape rather than use the API:
    * The X API v2 only exposes tweet impression counts to the *owner* of the
      account. To evaluate someone else's KOL value, we need the public
      tweet page — which shows view counts to logged-in users.
    * Scraping is fragile. If Twitter changes selectors, this file is the
      one place to fix.
"""

from __future__ import annotations

import asyncio
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from twitter_kol_eva.models import Sample


class TwitterAuthError(RuntimeError):
    """Raised when Twitter requires a login that the cookie file does not satisfy."""


class TwitterScrapeError(RuntimeError):
    """Raised when scraping fails for non-auth reasons (timeout, parse, etc.)."""


@dataclass
class ProfileResult:
    handle: str
    followers: int
    samples: list[Sample]


async def scrape_profile(
    handle: str,
    *,
    cookie_file: str | os.PathLike,
    recent_n: int = 20,
    headless: bool = True,
    request_timeout_ms: int = 20_000,
) -> ProfileResult:
    """Scrape a Twitter profile and return up to `recent_n` original tweets."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise TwitterScrapeError(
            "Playwright is not installed. Run: uv run playwright install chromium"
        ) from e

    cookie_path = Path(cookie_file).expanduser()
    if not cookie_path.exists():
        raise TwitterAuthError(
            f"Cookie file not found at {cookie_path}. "
            "Export your Twitter login cookies first — see README section "
            "'第一次安装：导出 Twitter Cookie'."
        )

    async with async_playwright() as p:
        # Prefer system Chrome (Twitter is friendlier to it), fall back to Chromium.
        browser = None
        for channel_attempt in ("chrome", None):
            try:
                kwargs: dict = {"headless": headless}
                if channel_attempt:
                    kwargs["channel"] = channel_attempt
                browser = await p.chromium.launch(**kwargs)
                break
            except Exception:
                continue
        if browser is None:
            raise TwitterScrapeError(
                "Could not launch any browser. Run: uv run playwright install chromium"
            )
        context = await browser.new_context(
            storage_state=str(cookie_path),
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        # Apply stealth to mask common automation flags (best-effort).
        try:
            from playwright_stealth import Stealth  # type: ignore

            await Stealth().apply_stealth_async(page)
        except Exception:
            pass

        try:
            await page.goto(
                f"https://x.com/{handle}",
                wait_until="networkidle",
                timeout=request_timeout_ms,
            )
        except Exception as e:
            await browser.close()
            raise TwitterScrapeError(
                f"Could not load https://x.com/{handle}: {e}. "
                "Check your network or whether the handle exists."
            ) from e

        # Login wall detection
        if "/login" in page.url or "/i/flow/login" in page.url:
            await browser.close()
            raise TwitterAuthError(
                "Twitter is asking us to log in. Your cookie file is missing or "
                "expired. Re-export it (see README) and try again."
            )

        # Followers
        followers = await _read_followers(page)

        # Tweets
        samples: list[Sample] = []
        seen_ids: set[str] = set()
        scroll_rounds = 0
        max_scrolls = max(8, recent_n // 2)

        while len(samples) < recent_n and scroll_rounds < max_scrolls:
            tweet_els = await page.locator('article[data-testid="tweet"]').all()
            for el in tweet_els:
                if len(samples) >= recent_n:
                    break
                sample = await _extract_sample(el)
                if sample is None or not sample.tweet_id:
                    continue
                if sample.tweet_id in seen_ids:
                    continue
                seen_ids.add(sample.tweet_id)
                samples.append(sample)
            await page.keyboard.press("End")
            await asyncio.sleep(random.uniform(1.5, 3.0))
            scroll_rounds += 1

        await browser.close()

    return ProfileResult(handle=handle, followers=followers, samples=samples)


async def _read_followers(page) -> int:
    """Read the follower count from the profile header."""
    try:
        # The profile header shows: "<n> Followers" — its anchor href ends with /followers.
        loc = page.locator('a[href$="/followers"] span span').first
        text = await loc.inner_text(timeout=5000)
        return _parse_count(text)
    except Exception:
        # Fallback: any /followers anchor with a number
        try:
            loc = page.locator('a[href$="/followers"]').first
            text = await loc.inner_text(timeout=5000)
            # Extract first number-with-suffix from the text
            m = re.search(r"([\d.,]+\s*[KM]?)", text)
            if m:
                return _parse_count(m.group(1))
        except Exception:
            pass
        return 0


async def _extract_sample(tweet_el) -> Optional[Sample]:
    """Extract a Sample from a single <article data-testid='tweet'> element."""
    try:
        # Skip retweets — they show a "X reposted" social context line.
        if await tweet_el.locator('[data-testid="socialContext"]').count() > 0:
            return None
    except Exception:
        pass

    tweet_id = ""
    url = ""
    posted_at = ""
    try:
        link_el = tweet_el.locator('a[href*="/status/"]').first
        href = await link_el.get_attribute("href")
        if href:
            url = f"https://x.com{href}" if href.startswith("/") else href
            m = re.search(r"/status/(\d+)", href)
            if m:
                tweet_id = m.group(1)
    except Exception:
        pass

    try:
        time_el = tweet_el.locator("time").first
        dt = await time_el.get_attribute("datetime")
        if dt:
            posted_at = dt
    except Exception:
        pass

    likes = await _read_count(tweet_el, '[data-testid="like"]')
    comments = await _read_count(tweet_el, '[data-testid="reply"]')
    shares = await _read_count(tweet_el, '[data-testid="retweet"]')
    views = await _read_views(tweet_el)

    return Sample(
        tweet_id=tweet_id,
        url=url,
        posted_at=posted_at,
        views=views,
        likes=likes,
        comments=comments,
        shares=shares,
    )


async def _read_count(tweet_el, testid_selector: str) -> int:
    try:
        # The number is rendered inside the button's accessible label or inner span.
        text = await tweet_el.locator(f"{testid_selector} span").first.inner_text(
            timeout=2000
        )
        return _parse_count(text)
    except Exception:
        return 0


async def _read_views(tweet_el) -> int:
    """Read the view/impression count, which lives on a separate analytics anchor."""
    try:
        # Most reliable: the anchor whose href ends with /analytics shows view count.
        analytics_el = tweet_el.locator('a[href$="/analytics"]').first
        text = await analytics_el.inner_text(timeout=2000)
        # Extract the leading number
        m = re.search(r"([\d.,]+\s*[KM]?)", text)
        if m:
            return _parse_count(m.group(1))
    except Exception:
        pass
    try:
        # Fallback: aria-label like "1,234 views. View post analytics"
        analytics_el = tweet_el.locator('[aria-label*="view"]').first
        label = await analytics_el.get_attribute("aria-label")
        if label:
            m = re.search(r"([\d.,]+)", label)
            if m:
                return _parse_count(m.group(1))
    except Exception:
        pass
    return 0


def _parse_count(text: str) -> int:
    """Parse '1.2K', '45M', '1,234' -> int."""
    if not text:
        return 0
    text = text.strip().replace(",", "").replace(" ", "")
    if not text or text == "0":
        return 0
    try:
        if text.endswith("K"):
            return int(float(text[:-1]) * 1_000)
        if text.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        if text.endswith("B"):
            return int(float(text[:-1]) * 1_000_000_000)
        return int(float(text))
    except ValueError:
        return 0
