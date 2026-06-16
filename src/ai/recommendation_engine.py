"""
TennisIQ MVP — AI Recommendation Engine v2
============================================
Now includes ATP benchmark data from Jeff Sackmann dataset
and recovery-performance correlation from Fernando's real data.
"""

import os
import re
import json
from datetime import date
from typing import Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def load_benchmarks(data_dir: str) -> dict:
    """Load ATP benchmarks"""
    try:
        with open(f"{data_dir}/benchmarks.json") as f:
            return json.load(f)
    except Exception:
        return {}


def build_prompt(player, today, history, psychology, nutrition, upcoming, benchmarks=None):
    history_lines = []
    for d in history[-7:]:
        if d.get("match_played"):
            match_line = f"MATCH {d.get('match_result','?')} {d.get('match_score','')}"
        else:
            match_line = f"Training: {d.get('session_type','?')} {d.get('session_minutes','?')}min"
        history_lines.append(
            f"  {d['date']}: Recovery {d.get('recovery_score','?')}% | "
            f"HRV {d.get('hrv_ms','?')}ms | Sleep {d.get('sleep_hours','?')}h | {match_line}"
        )
    history_text = "\n".join(history_lines) if history_lines else "  No history"

    recent = history[-7:] if len(history) >= 7 else history
    avg_recovery = round(sum(d.get("recovery_score", 70) for d in recent) / max(len(recent), 1))
    avg_hrv = round(sum(d.get("hrv_ms", 55) for d in recent) / max(len(recent), 1), 1)
    avg_sleep = round(sum(d.get("sleep_hours", 7) for d in recent) / max(len(recent), 1), 1)

    if len(history) >= 3:
        last3 = [d.get("recovery_score", 70) for d in history[-3:]]
        trend = "DECLINING" if last3[-1] < last3[0] - 8 else "IMPROVING" if last3[-1] > last3[0] + 8 else "STABLE"
    else:
        trend = "STABLE"

    psych_section = ""
    if psychology:
        psych_section = f"""
PSYCHOLOGY: APSQ {psychology.get('apsq_average','?')}/5 - {psychology.get('strain_level','?')}
  Pre-match anxiety: {psychology.get('pre_match_anxiety_1_10','?')}/10
  Notes: {psychology.get('coach_notes','')}"""

    nutr_section = ""
    if nutrition:
        nutr_section = f"""
NUTRITION: {nutrition.get('total_calories_kcal','?')} kcal | Protein {nutrition.get('protein_g','?')}g | Hydration {nutrition.get('hydration_liters','?')}L"""

    bench_section = ""
    if benchmarks:
        rec_perf = benchmarks.get("recovery_performance_correlation", {})
        atp = benchmarks.get("atp_tour_averages", {})
        targets = benchmarks.get("fernando_targets", {})
        bench_section = f"""
ATP BENCHMARKS (Jeff Sackmann dataset, 9500+ matches):
  ATP first serve avg: {atp.get('first_serve_pct','63')}% | Fernando target: {targets.get('first_serve_pct_target','60')}%
  ATP unforced errors: {atp.get('unforced_errors_per_player_per_match','21.8')}/match | Fernando target: {targets.get('unforced_errors_target','18')}
  ATP winners/match: {atp.get('winners_per_player_per_match','28.4')}
  Recovery-performance: wins {rec_perf.get('high_recovery_80plus',{}).get('win_rate',0.75)*100:.0f}% when recovery >80% vs {rec_perf.get('low_recovery_below_65',{}).get('win_rate',0.40)*100:.0f}% when <65%
  Key insight: {rec_perf.get('insight','')}"""

    return f"""You are a sports science advisor for a tennis academy AI platform.
Analyze this player data and generate a coaching recommendation.
Use the ATP benchmarks to provide context where relevant.

PLAYER: {player.get('name','?')}, Age {player.get('age','?')} | Level: {player.get('level','?')} | Surface: {player.get('preferred_surface','clay')}

TODAY {today.get('date','')}:
  Recovery: {today.get('recovery_score','?')}% (7-day avg: {avg_recovery}%)
  HRV: {today.get('hrv_ms','?')}ms (7-day avg: {avg_hrv}ms)
  Sleep: {today.get('sleep_hours','?')}h (7-day avg: {avg_sleep}h)
  Resting HR: {today.get('resting_hr_bpm','?')} bpm
  Trend: {trend}

LAST 7 DAYS:
{history_text}
{psych_section}
{nutr_section}
{bench_section}

SCHEDULE: Today: {upcoming.get('today','TBD')} | Next match: {upcoming.get('next_match','None')}

Respond in EXACTLY this format with no asterisks or markdown:

STATUS: GREEN

KEY FINDING:
One sentence about the most important insight from all data streams.

TODAYS RECOMMENDATION:
Specific actionable guidance for today. Reference actual numbers from the data.
Maximum 3 sentences.

CROSS DATA INSIGHT:
One insight that combines recovery data with match performance or ATP benchmarks.
Maximum 2 sentences.

WATCH THIS WEEK:
One specific metric to monitor with a threshold and action. Maximum 2 sentences."""


def generate_recommendation(player, today_data, history, psychology_data=None,
                            nutrition_data=None, upcoming_schedule=None, data_dir=None):
    upcoming = upcoming_schedule or {
        "today": "Training session",
        "tomorrow": "TBD",
        "next_match": "No match scheduled"
    }

    benchmarks = load_benchmarks(data_dir) if data_dir else {}

    prompt = build_prompt(player, today_data, history, psychology_data,
                         nutrition_data, upcoming, benchmarks)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )

        output_text = message.content[0].text

        status = "GREEN"
        if "STATUS: AMBER" in output_text.upper():
            status = "AMBER"
        elif "STATUS: RED" in output_text.upper():
            status = "RED"

        clean = re.sub(r"\*+", "", output_text)

        def extract(pattern):
            m = re.search(pattern, clean, re.DOTALL | re.IGNORECASE)
            return m.group(1).strip() if m else ""

        key_finding = extract(r"KEY FINDING:\s*\n(.*?)(?=\nTODAY|\nCROSS|\nWATCH|\Z)")
        today_rec = extract(r"TODAYS?\s*RECOMMENDATION:\s*\n(.*?)(?=\nCROSS|\nWATCH|\Z)")
        cross = extract(r"CROSS\s*DATA\s*INSIGHT:\s*\n(.*?)(?=\nWATCH|\Z)")
        watch = extract(r"WATCH\s*THIS\s*WEEK:\s*\n(.*?)(?=\Z)")

        sources = []
        if today_data.get("recovery_score") is not None:
            sources.append("whoop_recovery")
        if today_data.get("hrv_ms") is not None:
            sources.append("whoop_hrv")
        if today_data.get("strain_score") is not None:
            sources.append("whoop_strain")
        if today_data.get("match_played"):
            sources.append("match_results")
        if psychology_data:
            sources.append("psychology_apsq")
        if nutrition_data:
            sources.append("nutrition_log")
        if benchmarks:
            sources.append("atp_benchmarks")

        return {
            "player_id": player.get("player_id"),
            "player_name": player.get("name"),
            "date": str(date.today()),
            "status": status,
            "status_emoji": {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(status, "⚪"),
            "key_finding": key_finding,
            "today_recommendation": today_rec,
            "cross_data_insight": cross,
            "watch_this_week": watch,
            "full_text": output_text,
            "data_sources_used": sources,
            "generated_at": str(date.today()),
            "model": "claude-sonnet-4-6"
        }

    except Exception as e:
        return {
            "player_id": player.get("player_id"),
            "player_name": player.get("name"),
            "date": str(date.today()),
            "status": "ERROR",
            "status_emoji": "⚠️",
            "key_finding": f"Error: {str(e)}",
            "today_recommendation": "Check API key and data sources.",
            "cross_data_insight": "",
            "watch_this_week": "",
            "full_text": "",
            "data_sources_used": [],
            "generated_at": str(date.today()),
            "model": "claude-sonnet-4-6"
        }


def generate_morning_briefing(players_data):
    recommendations = []
    for p in players_data:
        rec = generate_recommendation(
            player=p["player"],
            today_data=p["today"],
            history=p["history"],
            psychology_data=p.get("psychology"),
            nutrition_data=p.get("nutrition"),
            upcoming_schedule=p.get("upcoming"),
            data_dir=p.get("data_dir")
        )
        recommendations.append(rec)

    counts = {"GREEN": 0, "AMBER": 0, "RED": 0, "ERROR": 0}
    for r in recommendations:
        counts[r.get("status", "ERROR")] += 1

    return {
        "generated_at": str(date.today()),
        "total_players": len(recommendations),
        "status_summary": counts,
        "recommendations": sorted(
            recommendations,
            key=lambda x: {"RED": 0, "AMBER": 1, "GREEN": 2, "ERROR": 3}.get(x["status"], 4)
        )
    }
