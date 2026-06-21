#!/usr/bin/env python3
"""
Script to run all example workflows and verify they work.
"""

from __future__ import annotations

import sys
import traceback

from rich.console import Console
from rich.table import Table

console = Console()


def run_example(name: str, fn, *args) -> bool:
    """Run a single example and return success status."""
    try:
        fn(*args)
        return True
    except Exception as exc:
        console.print(f"[red]FAILED: {name}[/red]")
        console.print(f"  Error: {exc}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return False


def main() -> None:
    from examples.financial_analysis_agent import run_financial_analysis
    from examples.news_monitoring_agent import run_news_monitoring
    from examples.resume_review_agent import SAMPLE_RESUME, run_resume_review
    from examples.stock_research_agent import run_stock_research

    examples = [
        ("Stock Research (AAPL)", run_stock_research, "AAPL"),
        ("Financial Analysis (Apple)", run_financial_analysis, "Apple Inc.", "Q4 2024"),
        ("News Monitoring (AI)", run_news_monitoring, "artificial intelligence"),
        ("Resume Review", run_resume_review, SAMPLE_RESUME),
    ]

    results: list[tuple[str, bool]] = []
    for name, fn, *args in examples:
        console.print(f"\n[bold]Running: {name}[/bold]")
        success = run_example(name, fn, *args)
        results.append((name, success))

    table = Table(title="Example Results")
    table.add_column("Example")
    table.add_column("Status")

    all_passed = True
    for name, passed in results:
        status = "[green]PASSED[/green]" if passed else "[red]FAILED[/red]"
        table.add_row(name, status)
        if not passed:
            all_passed = False

    console.print(table)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
