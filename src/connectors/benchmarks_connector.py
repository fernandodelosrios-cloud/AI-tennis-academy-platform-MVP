"""
TennisIQ MVP — Benchmarks Connector
=====================================
Loads ATP benchmark data from Jeff Sackmann's dataset
and cross-references with Fernando's personal performance.

Source: github.com/JeffSackmann/tennis_MatchChartingProject
License: CC BY-NC-SA 4.0 — Attribution required, non-commercial only
"""

import json
from pathlib import Path


def load_benchmarks(data_dir: Path) -> dict:
    """Load ATP benchmarks from local file"""
    try:
        with open(data_dir / "benchmarks.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get_fernando_vs_benchmark(matches: list, benchmarks: dict) -> dict:
    """
    Cross-reference Fernando's real match data
    against ATP and recreational benchmarks.
    Returns insights for the AI recommendation engine.
    """
    if not matches:
        return {}

    wins = sum(1 for m in matches if m.get("result") == "W")
    total = len(matches)
    win_rate = wins / total if total > 0 else 0

    # Recovery on match days
    high_recovery_matches = [m for m in matches if m.get("recovery_on_match_day", 0) >= 80]
    low_recovery_matches = [m for m in matches if m.get("recovery_on_match_day", 0) < 65]

    high_rec_wins = sum(1 for m in high_recovery_matches if m.get("result") == "W")
    low_rec_wins = sum(1 for m in low_recovery_matches if m.get("result") == "W")

    high_rec_win_rate = high_rec_wins / len(high_recovery_matches) if high_recovery_matches else 0
    low_rec_win_rate = low_rec_wins / len(low_recovery_matches) if low_recovery_matches else 0

    rec_benchmark = benchmarks.get("recreational_advanced_benchmarks", {})
    atp_avg = benchmarks.get("atp_tour_averages", {})

    return {
        "fernando_win_rate": round(win_rate * 100, 1),
        "benchmark_win_rate": rec_benchmark.get("win_rate_vs_similar", 0.50) * 100,
        "above_benchmark": win_rate > rec_benchmark.get("win_rate_vs_similar", 0.50),
        "high_recovery_win_rate": round(high_rec_win_rate * 100, 1),
        "low_recovery_win_rate": round(low_rec_win_rate * 100, 1),
        "recovery_impact": round((high_rec_win_rate - low_rec_win_rate) * 100, 1),
        "atp_first_serve_pct": atp_avg.get("first_serve_pct", 63.0),
        "fernando_first_serve_target": 60.0,
        "atp_unforced_errors": atp_avg.get("unforced_errors_per_player_per_match", 21.8),
        "fernando_unforced_target": 18,
        "key_insight": (
            f"Fernando wins {round(high_rec_win_rate*100)}% of matches with recovery >80% "
            f"vs {round(low_rec_win_rate*100)}% with recovery <65%. "
            f"Recovery is Fernando's most controllable performance variable."
            if high_recovery_matches and low_recovery_matches
            else "Building recovery-performance correlation — need more match data."
        )
    }
