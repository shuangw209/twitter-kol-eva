"""Command-line entry point.

Usage:
    tweval evaluate <account_or_url> --price 500
    tweval evaluate https://x.com/elonmusk --price 500 --recent-n 30 --currency USD
    tweval evaluate elonmusk --price 500 --json out.json
    tweval doctor                       # check that cookies + Playwright are ready

Environment variables (read from .env if python-dotenv is installed, else from
the real environment):
    TWITTER_COOKIE_FILE   path to the exported cookie JSON
    DEFAULT_CURRENCY      USD by default
    DEFAULT_RECENT_N      20 by default
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console

from twitter_kol_eva.calculator import calculate_metrics
from twitter_kol_eva.report import render_table, to_json, write_json_file
from twitter_kol_eva.scraper import (
    TwitterAuthError,
    TwitterScrapeError,
    scrape_profile,
)
from twitter_kol_eva.url_utils import parse_handle, profile_url


def _load_env() -> None:
    """Load .env into os.environ if python-dotenv is available; otherwise no-op."""
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except ImportError:
        # .env support is optional; environment vars still work.
        pass


@click.group()
@click.version_option(package_name="twitter-kol-eva")
def main() -> None:
    """Twitter/X KOL quick evaluator."""
    _load_env()


@main.command()
@click.argument("account_or_url")
@click.option("--price", "-p", type=float, required=True, help="Quoted price for one sponsored tweet.")
@click.option(
    "--recent-n",
    "-n",
    type=int,
    default=None,
    help="How many recent original tweets to sample (default 20, env DEFAULT_RECENT_N).",
)
@click.option(
    "--currency",
    "-c",
    default=None,
    help="Currency label for the price (default USD, env DEFAULT_CURRENCY).",
)
@click.option(
    "--cookie-file",
    type=click.Path(),
    default=None,
    help="Path to the Twitter cookie JSON (default env TWITTER_COOKIE_FILE).",
)
@click.option(
    "--json",
    "json_path",
    type=click.Path(),
    default=None,
    help="If set, also write the full JSON report to this path.",
)
@click.option("--no-table", is_flag=True, help="Suppress the terminal table; print JSON to stdout instead.")
@click.option("--headed", is_flag=True, help="Show the browser window (debug mode).")
def evaluate(
    account_or_url: str,
    price: float,
    recent_n: int | None,
    currency: str | None,
    cookie_file: str | None,
    json_path: str | None,
    no_table: bool,
    headed: bool,
) -> None:
    """Scrape recent tweets, compute the 6 metrics, and report."""
    console = Console()

    try:
        handle = parse_handle(account_or_url)
    except ValueError as e:
        console.print(f"[red]Bad input:[/red] {e}")
        sys.exit(2)

    cookie_file = cookie_file or os.environ.get("TWITTER_COOKIE_FILE")
    if not cookie_file:
        console.print(
            "[red]No cookie file configured.[/red] Set TWITTER_COOKIE_FILE in .env "
            "or pass --cookie-file. See README for how to export cookies."
        )
        sys.exit(2)

    recent_n = recent_n or int(os.environ.get("DEFAULT_RECENT_N", "20"))
    currency = currency or os.environ.get("DEFAULT_CURRENCY", "USD")

    console.print(
        f"[cyan]Scraping[/cyan] @{handle} — sampling up to {recent_n} recent original tweets…"
    )

    try:
        result = asyncio.run(
            scrape_profile(
                handle,
                cookie_file=cookie_file,
                recent_n=recent_n,
                headless=not headed,
            )
        )
    except TwitterAuthError as e:
        console.print(f"[red]Auth problem:[/red] {e}")
        sys.exit(3)
    except TwitterScrapeError as e:
        console.print(f"[red]Scrape failed:[/red] {e}")
        sys.exit(4)

    if not result.samples:
        console.print(
            "[yellow]Warning:[/yellow] no tweets were collected. "
            "Either the profile has no original tweets, or scraping was blocked. "
            "Try --headed to watch what happens."
        )

    report = calculate_metrics(
        handle=result.handle,
        profile_url=profile_url(result.handle),
        followers=result.followers,
        samples=result.samples,
        price=price,
        currency=currency,
    )

    if no_table:
        click.echo(to_json(report))
    else:
        render_table(report, console=console)

    if json_path:
        write_json_file(report, json_path)
        console.print(f"[green]Wrote[/green] JSON report to [bold]{json_path}[/bold]")


@main.command()
@click.option(
    "--cookie-file",
    type=click.Path(),
    default=None,
    help="Where to save the cookie JSON (default env TWITTER_COOKIE_FILE).",
)
def login(cookie_file: str | None) -> None:
    """Open a real browser window so you can log in to Twitter, then save cookies.

    Steps:
        1. A Chromium window opens.
        2. You log in to https://x.com manually (username + password + any 2FA).
        3. Once you're on your home timeline, come back to this terminal and
           press Enter. The cookies will be saved to the file you configured.

    You only need to do this once every few weeks (or whenever scraping fails
    with an auth error).
    """
    cookie_file = cookie_file or os.environ.get("TWITTER_COOKIE_FILE")
    if not cookie_file:
        click.echo(
            "No cookie file path configured. Pass --cookie-file PATH or set "
            "TWITTER_COOKIE_FILE in .env.",
            err=True,
        )
        sys.exit(2)

    target = Path(cookie_file).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    asyncio.run(_login_flow(str(target)))


async def _login_flow(target_path: str) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        click.echo("Playwright not installed. Run: uv sync && uv run playwright install chromium", err=True)
        sys.exit(2)

    console = Console()
    console.print(
        "[cyan]Opening a Chromium window — log in to https://x.com, then come back here.[/cyan]"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://x.com/login", wait_until="domcontentloaded")

        click.echo("\nWhen you've logged in and you can see your home timeline,")
        click.echo("press [Enter] here to save cookies and close the browser.")
        click.prompt("Ready?", default="", show_default=False)

        await context.storage_state(path=target_path)
        await browser.close()

    console.print(f"[green]✓[/green] Cookies saved to [bold]{target_path}[/bold]")


@main.command()
def doctor() -> None:
    """Check that Playwright is installed and the cookie file looks usable."""
    console = Console()
    ok = True

    # Playwright import
    try:
        import playwright  # noqa: F401

        console.print("[green]✓[/green] Playwright is installed.")
    except ImportError:
        console.print("[red]✗[/red] Playwright is NOT installed. Run: uv sync")
        ok = False

    # Browser binary
    try:
        from playwright.async_api import async_playwright  # noqa: F401

        console.print("[green]✓[/green] Playwright Python API loadable.")
    except Exception as e:
        console.print(f"[red]✗[/red] Playwright API not loadable: {e}")
        ok = False

    # Cookie file
    cookie_file = os.environ.get("TWITTER_COOKIE_FILE")
    if not cookie_file:
        console.print("[yellow]![/yellow] TWITTER_COOKIE_FILE is not set in env.")
        ok = False
    else:
        path = Path(cookie_file).expanduser()
        if not path.exists():
            console.print(f"[red]✗[/red] Cookie file not found: {path}")
            ok = False
        else:
            try:
                import json

                with open(path) as f:
                    data = json.load(f)
                cookies = data.get("cookies", []) if isinstance(data, dict) else []
                console.print(
                    f"[green]✓[/green] Cookie file readable ({len(cookies)} cookies)."
                )
                names = {c.get("name") for c in cookies if isinstance(c, dict)}
                if "auth_token" not in names and "ct0" not in names:
                    console.print(
                        "[yellow]![/yellow] Cookie file is missing auth_token / ct0 — "
                        "Twitter may treat this as logged-out. Re-export."
                    )
            except Exception as e:
                console.print(f"[red]✗[/red] Cookie file unreadable: {e}")
                ok = False

    if ok:
        console.print("\n[bold green]All checks passed.[/bold green] You can run `tweval evaluate ...`.")
    else:
        console.print("\n[bold red]Some checks failed.[/bold red] See README troubleshooting section.")
        sys.exit(1)


if __name__ == "__main__":
    main()
