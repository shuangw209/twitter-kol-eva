"""Report formatting: pretty terminal table + JSON dump."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from twitter_kol_eva.models import Report


def to_json(report: Report, *, pretty: bool = True) -> str:
    return json.dumps(
        report.to_dict(),
        indent=2 if pretty else None,
        ensure_ascii=False,
    )


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def _fmt_num(x: float) -> str:
    if x >= 1_000_000:
        return f"{x / 1_000_000:.2f}M"
    if x >= 1_000:
        return f"{x / 1_000:.2f}K"
    return f"{x:.0f}"


def _fmt_money(x: float, currency: str) -> str:
    return f"{currency} {x:,.2f}"


def render_table(report: Report, console: Console | None = None) -> None:
    """Print a friendly summary to the terminal."""
    console = console or Console()

    head = Table.grid(padding=(0, 2))
    head.add_column(justify="right", style="bold")
    head.add_column()
    head.add_row("Account", f"@{report.handle}  ({report.profile_url})")
    head.add_row("Followers", _fmt_num(report.followers))
    head.add_row("Quoted price", _fmt_money(report.price, report.currency))
    head.add_row("Sample size", f"{report.sample_size} recent original tweets")
    head.add_row(
        "Avg per tweet",
        f"views {_fmt_num(report.avg_views)} | likes {_fmt_num(report.avg_likes)} | "
        f"comments {_fmt_num(report.avg_comments)} | shares {_fmt_num(report.avg_shares)}",
    )
    console.print(Panel(head, title="KOL Snapshot", border_style="cyan"))

    metrics = report.metrics
    t = Table(title="The 6 Metrics", header_style="bold magenta", show_lines=False)
    t.add_column("Metric", style="bold")
    t.add_column("Value", justify="right")
    t.add_column("Formula", style="dim")
    t.add_row("ER (粉丝互动率)", _fmt_pct(metrics.er), "(likes+comments+shares) / followers")
    t.add_row("View ER (曝光互动率)", _fmt_pct(metrics.view_er), "(likes+comments+shares) / avg_views")
    t.add_row("C/L Ratio (评论深度比)", _fmt_pct(metrics.cl_ratio), "comments / likes")
    t.add_row("Reach Rate (粉丝触达率)", _fmt_pct(metrics.reach_rate), "avg_views / followers")
    t.add_row("Stability (数据稳定性)", f"{metrics.stability:.2f}x", "max_views / min_views")
    t.add_row("CPM (千次曝光成本)", _fmt_money(metrics.cpm, report.currency), "price / (avg_views/1000)")
    console.print(t)

    if report.notes:
        notes_panel = "\n".join(f"• {n}" for n in report.notes)
        console.print(
            Panel(notes_panel, title="Notes", border_style="yellow", title_align="left")
        )

    if report.samples:
        s = Table(title=f"Samples ({len(report.samples)})", show_lines=False)
        s.add_column("#", justify="right", style="dim")
        s.add_column("Posted")
        s.add_column("Views", justify="right")
        s.add_column("Likes", justify="right")
        s.add_column("Comments", justify="right")
        s.add_column("Shares", justify="right")
        s.add_column("URL", style="dim", overflow="fold")
        for i, sample in enumerate(report.samples, 1):
            s.add_row(
                str(i),
                sample.posted_at[:10] if sample.posted_at else "—",
                _fmt_num(sample.views),
                _fmt_num(sample.likes),
                _fmt_num(sample.comments),
                _fmt_num(sample.shares),
                sample.url or "—",
            )
        console.print(s)


def write_json_file(report: Report, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_json(report))
