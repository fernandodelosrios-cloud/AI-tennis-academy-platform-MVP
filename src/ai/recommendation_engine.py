"""
Orbis AI — Multi-Agent Debate Engine
======================================
Architecture:
  Round 1A: Claude (sports science angle) analyzes player data
  Round 1B: Gemini (pattern recognition angle) analyzes same data
  Round 2:  Claude synthesis reads both, identifies agreements/disagreements,
            produces final recommendation

Setup:
  1. Anthropic key: console.anthropic.com -> ANTHROPIC_API_KEY in .env
  2. Gemini key FREE: aistudio.google.com -> GEMINI_API_KEY in .env
  3. pip install google-generativeai
"""

import os
import re
import json
from datetime import date
from typing import Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ── Clients ───────────────────────────────────────────────────────────────────
anthropic_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)


def get_gemini_client():
    """Initialize Gemini 1.5 Flash — returns None if not configured"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("   ⚠️  GEMINI_API_KEY not set — running Claude-only mode")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # Use 1.5-flash — more reliable structured output than 2.5-flash
        return genai.GenerativeModel("gemini-2.0-flash")
    except ImportError:
        print("   ⚠️  google-generativeai not installed. Run: pip install google-generativeai")
        return None
    except Exception as e:
        print(f"   ⚠️  Gemini init error: {e}")
        return None


# ── Context builder ───────────────────────────────────────────────────────────

def build_player_context(player, today_data, history, psychology,
                         nutrition, upcoming, benchmarks=None):
    recent = history[-7:] if len(history) >= 7 else history
    avg_rec = round(sum(d.get("recovery_score", 70) for d in recent) /
                    max(len(recent), 1))
    avg_hrv = round(sum(d.get("hrv_ms", 55) for d in recent) /
                    max(len(recent), 1), 1)
    avg_sleep = round(sum(d.get("sleep_hours", 7) for d in recent) /
                      max(len(recent), 1), 1)

    if len(history) >= 3:
        last3 = [d.get("recovery_score", 70) for d in history[-3:]]
        trend = ("DECLINING" if last3[-1] < last3[0] - 8
                 else "IMPROVING" if last3[-1] > last3[0] + 8
                 else "STABLE")
    else:
        trend = "STABLE"

    history_lines = []
    for d in history[-7:]:
        ml = (f"MATCH {d.get('match_result','?')} {d.get('match_score','')}"
              if d.get("match_played")
              else f"Training: {d.get('session_type','?')} "
                   f"{d.get('session_minutes','?')}min RPE {d.get('session_rpe','?')}")
        history_lines.append(
            f"  {d['date']}: Recovery {d.get('recovery_score','?')}% | "
            f"HRV {d.get('hrv_ms','?')}ms | Sleep {d.get('sleep_hours','?')}h | {ml}"
        )

    psych_ctx = ""
    if psychology:
        psych_ctx = f"""
PSYCHOLOGY (APSQ): {psychology.get('apsq_average','?')}/5 — {psychology.get('strain_level','?')}
  Pre-match anxiety: {psychology.get('pre_match_anxiety_1_10','?')}/10
  Self-talk: {psychology.get('self_talk_quality_1_10','?')}/10
  Notes: {psychology.get('coach_notes','None')}"""

    nutr_ctx = ""
    if nutrition:
        nutr_ctx = f"""
NUTRITION (yesterday): {nutrition.get('total_calories_kcal','?')} kcal | \
Protein {nutrition.get('protein_g','?')}g | \
Hydration {nutrition.get('hydration_liters','?')}L"""

    bench_ctx = ""
    if benchmarks:
        atp = benchmarks.get("atp_tour_averages", {})
        corr = benchmarks.get("recovery_performance_correlation", {})
        bench_ctx = f"""
ATP BENCHMARKS: First serve {atp.get('first_serve_pct',63)}% avg | \
Winners {atp.get('winners_per_player_per_match',28.4)}/match avg
Recovery-win correlation: {corr.get('high_recovery_80plus',{}).get('win_rate',0.75)*100:.0f}% \
wins when recovery >80% vs {corr.get('low_recovery_below_65',{}).get('win_rate',0.40)*100:.0f}% when <65%"""

    return f"""PLAYER: {player.get('name','?')}, Age {player.get('age','?')} | \
Level: {player.get('level','?')} | Surface: {player.get('preferred_surface','clay')}

TODAY {today_data.get('date', str(date.today()))}:
  Recovery: {today_data.get('recovery_score','?')}% (7-day avg: {avg_rec}%)
  HRV: {today_data.get('hrv_ms','?')}ms (7-day avg: {avg_hrv}ms)
  Sleep: {today_data.get('sleep_hours','?')}h (7-day avg: {avg_sleep}h)
  Resting HR: {today_data.get('resting_hr_bpm','?')} bpm | Strain: {today_data.get('strain_score','?')}/21
  3-day trend: {trend}

LAST 7 DAYS:
{chr(10).join(history_lines)}
{psych_ctx}
{nutr_ctx}
{bench_ctx}

SCHEDULE: Today: {upcoming.get('today','Training')} | Next match: {upcoming.get('next_match','TBD')}"""


# ── Agent 1: Claude Sports Science ───────────────────────────────────────────

def run_claude_agent(context: str) -> dict:
    """
    Claude analyzes from a sports science / periodization angle.
    Focus: training load, HRV interpretation, injury prevention, recovery.
    """
    prompt = f"""You are a sports science specialist analyzing a tennis player.
Focus on: training load, HRV patterns, recovery science, injury prevention.

{context}

Respond in EXACTLY this format — no extra text before or after:

STATUS: [GREEN or AMBER or RED]

SPORTS_SCIENCE_ASSESSMENT:
[2-3 sentences about physiological readiness from a sports science perspective]

SPORTS_SCIENCE_RECOMMENDATION:
[2-3 specific sentences about today's training — include RPE and duration]

SPORTS_SCIENCE_RISK_FLAG:
[1-2 sentences about the main risk — include a specific threshold to watch]

SPORTS_SCIENCE_CONFIDENCE: [HIGH or MEDIUM or LOW]
SPORTS_SCIENCE_CONFIDENCE_REASON: [One sentence]"""

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.replace("**", "")

    def extract(start_marker, stop_markers):
        idx = text.find(start_marker + ":")
        if idx == -1:
            return ""
        start = idx + len(start_marker) + 1
        while start < len(text) and text[start] in "\n ":
            start += 1
        end = len(text)
        for sm in stop_markers:
            si = text.find(sm + ":", start)
            if si != -1 and si < end:
                end = si
        return text[start:end].strip()

    status = "GREEN"
    if "STATUS: AMBER" in text.upper():
        status = "AMBER"
    elif "STATUS: RED" in text.upper():
        status = "RED"

    conf_raw = extract("SPORTS_SCIENCE_CONFIDENCE", ["SPORTS_SCIENCE_CONFIDENCE_REASON"])
    conf_m = re.search(r"(HIGH|MEDIUM|LOW)", conf_raw.upper())

    return {
        "agent": "Claude — Sports Science",
        "model": "claude-sonnet-4-6",
        "status": status,
        "assessment": extract("SPORTS_SCIENCE_ASSESSMENT",
                              ["SPORTS_SCIENCE_RECOMMENDATION",
                               "SPORTS_SCIENCE_RISK_FLAG",
                               "SPORTS_SCIENCE_CONFIDENCE"]),
        "recommendation": extract("SPORTS_SCIENCE_RECOMMENDATION",
                                  ["SPORTS_SCIENCE_RISK_FLAG",
                                   "SPORTS_SCIENCE_CONFIDENCE"]),
        "risk_flag": extract("SPORTS_SCIENCE_RISK_FLAG",
                             ["SPORTS_SCIENCE_CONFIDENCE"]),
        "confidence": conf_m.group(1) if conf_m else "MEDIUM",
        "confidence_reason": extract("SPORTS_SCIENCE_CONFIDENCE_REASON", []),
        "raw": text
    }


# ── Agent 2: Gemini Pattern Recognition ──────────────────────────────────────

def run_gemini_agent(context: str, gemini_model) -> dict:
    """
    Gemini analyzes from a cross-domain pattern recognition angle.
    Focus: non-obvious correlations, psychological-physical interactions,
    performance trends across multiple data streams.
    """
    if gemini_model is None:
        return {
            "agent": "Gemini — Pattern Recognition",
            "model": "not configured",
            "status": "UNAVAILABLE",
            "assessment": "Add GEMINI_API_KEY to .env to enable Gemini agent.",
            "recommendation": "",
            "risk_flag": "",
            "confidence": "N/A",
            "confidence_reason": "API key not configured",
            "raw": "",
            "available": False
        }

    prompt = f"""Analyze this tennis player data and fill in the template below.
You are looking for PATTERNS across multiple data streams — not just single metrics.
Focus on correlations between recovery, psychology, nutrition, and match performance.

{context}

Fill in EVERY section of this template. Do not skip any section.

STATUS: [GREEN or AMBER or RED]

PATTERN_ASSESSMENT:
[2-3 sentences about patterns you see ACROSS multiple data streams. What correlations exist?]

PATTERN_RECOMMENDATION:
[2-3 sentences about what today's training should look like based on these patterns]

PATTERN_UNIQUE_INSIGHT:
[1-2 sentences about an insight that ONLY emerges from combining multiple data streams]

PATTERN_CONFIDENCE: [HIGH or MEDIUM or LOW]
PATTERN_CONFIDENCE_REASON: [One sentence about your confidence level]"""

    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 600,
                "candidate_count": 1,
            }
        )
        text = response.text.replace("**", "")

        def extract(start_marker, stop_markers):
            idx = text.find(start_marker + ":")
            if idx == -1:
                # Try case-insensitive
                lower = text.lower()
                idx = lower.find(start_marker.lower() + ":")
            if idx == -1:
                return ""
            start = idx + len(start_marker) + 1
            while start < len(text) and text[start] in "\n ":
                start += 1
            end = len(text)
            for sm in stop_markers:
                si = text.find(sm + ":", start)
                if si == -1:
                    si = text.lower().find(sm.lower() + ":", start)
                if si != -1 and si < end:
                    end = si
            return text[start:end].strip()

        status = "GREEN"
        upper = text.upper()
        if "STATUS: AMBER" in upper:
            status = "AMBER"
        elif "STATUS: RED" in upper:
            status = "RED"

        assessment = extract("PATTERN_ASSESSMENT",
                             ["PATTERN_RECOMMENDATION",
                              "PATTERN_UNIQUE_INSIGHT",
                              "PATTERN_CONFIDENCE"])
        recommendation = extract("PATTERN_RECOMMENDATION",
                                 ["PATTERN_UNIQUE_INSIGHT",
                                  "PATTERN_CONFIDENCE"])
        unique = extract("PATTERN_UNIQUE_INSIGHT", ["PATTERN_CONFIDENCE"])
        conf_raw = extract("PATTERN_CONFIDENCE", ["PATTERN_CONFIDENCE_REASON"])
        conf_m = re.search(r"(HIGH|MEDIUM|LOW)", conf_raw.upper())
        confidence = conf_m.group(1) if conf_m else "MEDIUM"
        confidence_reason = extract("PATTERN_CONFIDENCE_REASON", [])

        # Fallback: if parsing failed, extract content from unstructured text
        if not assessment:
            lines = [l.strip() for l in text.split("\n")
                     if l.strip() and not any(m in l.upper() for m in
                     ["PATTERN_", "STATUS:", "STATUS "])]
            assessment = " ".join(lines[:3]) if lines else text[:300]
            if not recommendation:
                recommendation = " ".join(lines[3:6]) if len(lines) > 3 else ""
            if not unique:
                unique = " ".join(lines[6:8]) if len(lines) > 6 else ""
            confidence = confidence or "MEDIUM"
            confidence_reason = confidence_reason or "Extracted from unstructured response"

        return {
            "agent": "Gemini — Pattern Recognition",
            "model": "gemini-2.0-flash",
            "status": status,
            "assessment": assessment,
            "recommendation": recommendation,
            "risk_flag": unique,
            "confidence": confidence,
            "confidence_reason": confidence_reason,
            "raw": text,
            "available": True
        }

    except Exception as e:
        err_str = str(e)
        # Handle rate limit specifically
        if "429" in err_str or "quota" in err_str.lower():
            msg = "Gemini rate limit reached (free tier: 15 req/min). Running Claude-only this cycle."
        elif "404" in err_str or "not found" in err_str.lower():
            msg = "Gemini model not found. Check model name in get_gemini_client()."
        else:
            msg = f"Gemini error: {err_str[:100]}"
        
        print(f"   ⚠️  {msg}")
        return {
            "agent": "Gemini — Pattern Recognition",
            "model": "gemini-2.0-flash",
            "status": "UNAVAILABLE",
            "assessment": msg,
            "recommendation": "",
            "risk_flag": "",
            "confidence": "N/A",
            "confidence_reason": msg,
            "raw": "",
            "available": False
        }


# ── Round 2: Synthesis Agent ──────────────────────────────────────────────────

def run_synthesis_agent(player_name: str, context: str,
                        claude_result: dict, gemini_result: dict) -> dict:
    """
    Reads both agent assessments, finds agreements/disagreements,
    produces the final unified coaching recommendation.
    """
    gemini_available = gemini_result.get("available", False)

    if gemini_available:
        agents_text = f"""AGENT 1 — Claude (Sports Science):
  Status: {claude_result['status']}
  Assessment: {claude_result['assessment']}
  Recommendation: {claude_result['recommendation']}
  Risk flag: {claude_result['risk_flag']}
  Confidence: {claude_result['confidence']}

AGENT 2 — Gemini (Pattern Recognition):
  Status: {gemini_result['status']}
  Assessment: {gemini_result['assessment']}
  Recommendation: {gemini_result['recommendation']}
  Unique insight: {gemini_result['risk_flag']}
  Confidence: {gemini_result['confidence']}"""

        instruction = """You are the Synthesis Agent for Orbis AI.
Two AI agents independently analyzed the same player data.
Your job:
1. Find where both agents AGREE (high confidence)
2. Find where they DISAGREE (flag for coach)
3. Produce one clear final recommendation that is BETTER than either alone
4. If agents disagree on status, choose conservatively"""
    else:
        agents_text = f"""AGENT 1 — Claude (Sports Science):
  Status: {claude_result['status']}
  Assessment: {claude_result['assessment']}
  Recommendation: {claude_result['recommendation']}
  Risk flag: {claude_result['risk_flag']}
  Confidence: {claude_result['confidence']}

AGENT 2 — Gemini: Not available"""

        instruction = """You are the Synthesis Agent for Orbis AI.
Only one agent assessment is available. Produce the final recommendation
based on Claude's assessment."""

    prompt = f"""{instruction}

{context}

AGENT ASSESSMENTS:
{agents_text}

Produce the final coaching recommendation for {player_name}.
No asterisks or markdown formatting.

STATUS: [GREEN or AMBER or RED]

KEY FINDING:
[Most important single insight — 1-2 sentences]

TODAYS RECOMMENDATION:
[Specific actionable guidance for today — reference actual numbers — 2-3 sentences]

CROSS DATA INSIGHT:
[Best insight from combining multiple data streams — 2 sentences]

WATCH THIS WEEK:
[Specific metric with threshold and action — 1-2 sentences]

AGENT CONSENSUS: [FULL AGREEMENT or PARTIAL AGREEMENT or DISAGREEMENT]

DISAGREEMENT FLAGS:
[List disagreements as: "Topic: Claude said X. Gemini said Y." — or write NONE]

CONFIDENCE LEVEL: [HIGH or MEDIUM or LOW]"""

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text

    def extract(pattern):
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    status = "GREEN"
    if "STATUS: AMBER" in text.upper():
        status = "AMBER"
    elif "STATUS: RED" in text.upper():
        status = "RED"

    conf_m = re.search(r"CONFIDENCE LEVEL[:\s]+([A-Z]+)", text, re.IGNORECASE)
    consensus_m = re.search(
        r"AGENT CONSENSUS[:\s]+(FULL AGREEMENT|PARTIAL AGREEMENT|DISAGREEMENT)",
        text, re.IGNORECASE
    )

    return {
        "status": status,
        "status_emoji": {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(status, "⚪"),
        "key_finding": extract(r"KEY FINDING:\n(.*?)(?=\nTODAYS|\nCROSS|\nWATCH|\nAGENT|\Z)"),
        "today_recommendation": extract(r"TODAYS?\s*RECOMMENDATION:\n(.*?)(?=\nCROSS|\nWATCH|\nAGENT|\Z)"),
        "cross_data_insight": extract(r"CROSS\s*DATA\s*INSIGHT:\n(.*?)(?=\nWATCH|\nAGENT|\Z)"),
        "watch_this_week": extract(r"WATCH\s*THIS\s*WEEK:\n(.*?)(?=\nAGENT|\Z)"),
        "agent_consensus": consensus_m.group(1) if consensus_m else "PARTIAL AGREEMENT",
        "disagreement_flags": extract(r"DISAGREEMENT FLAGS:\n(.*?)(?=\nCONFIDENCE|\Z)"),
        "confidence_level": conf_m.group(1) if conf_m else "MEDIUM",
        "full_text": text,
        "agents_used": (["claude-sonnet-4-6", "gemini-1.5-flash"]
                        if gemini_available else ["claude-sonnet-4-6"]),
        "gemini_available": gemini_available,
        "generated_at": str(date.today())
    }


# ── Main orchestrator ─────────────────────────────────────────────────────────

def generate_debate_recommendation(
    player: dict,
    today_data: dict,
    history: list,
    psychology_data: Optional[dict] = None,
    nutrition_data: Optional[dict] = None,
    upcoming_schedule: Optional[dict] = None,
    data_dir: Optional[str] = None
) -> dict:
    """
    Full multi-agent debate pipeline.
    Falls back gracefully to Claude-only if Gemini is not configured.
    """
    upcoming = upcoming_schedule or {
        "today": "Training session",
        "tomorrow": "TBD",
        "next_match": "No match scheduled"
    }

    # Load benchmarks
    benchmarks = {}
    if data_dir:
        try:
            with open(f"{data_dir}/benchmarks.json") as f:
                benchmarks = json.load(f)
        except Exception:
            pass

    context = build_player_context(
        player, today_data, history,
        psychology_data, nutrition_data,
        upcoming, benchmarks
    )

    gemini_model = get_gemini_client()

    print(f"\n🤖 Orbis AI — Multi-Agent Debate for {player.get('name','?')}")
    print(f"   Agent 1: Claude (claude-sonnet-4-6) — Sports Science")
    print(f"   Agent 2: {'Gemini (gemini-1.5-flash) — Pattern Recognition' if gemini_model else 'Gemini (not configured)'}")
    print(f"   Round 1: Independent assessments...")

    claude_result = run_claude_agent(context)
    gemini_result = run_gemini_agent(context, gemini_model)

    print(f"   ✅ Claude: {claude_result['status']} | confidence: {claude_result['confidence']}")
    print(f"   {'✅' if gemini_result.get('available') else '⚠️ '} Gemini: {gemini_result['status']} | confidence: {gemini_result['confidence']}")
    print(f"   Round 2: Synthesis...")

    synthesis = run_synthesis_agent(
        player.get("name", "Player"),
        context,
        claude_result,
        gemini_result
    )

    print(f"   ✅ Final: {synthesis['status']} | Consensus: {synthesis['agent_consensus']} | Confidence: {synthesis['confidence_level']}")

    # Build sources list
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
    if gemini_result.get("available"):
        sources.append("gemini_debate")

    return {
        # Standard fields — compatible with existing dashboard
        "player_id": player.get("player_id"),
        "player_name": player.get("name"),
        "date": str(date.today()),
        "status": synthesis["status"],
        "status_emoji": synthesis["status_emoji"],
        "key_finding": synthesis["key_finding"],
        "today_recommendation": synthesis["today_recommendation"],
        "cross_data_insight": synthesis["cross_data_insight"],
        "watch_this_week": synthesis["watch_this_week"],
        "full_text": synthesis["full_text"],
        "data_sources_used": sources,
        "generated_at": str(date.today()),
        "model": "multi-agent-debate",

        # Debate-specific fields for the dashboard debate panel
        "debate": {
            "agents_used": synthesis["agents_used"],
            "gemini_available": synthesis["gemini_available"],
            "agent_consensus": synthesis["agent_consensus"],
            "disagreement_flags": synthesis["disagreement_flags"],
            "confidence_level": synthesis["confidence_level"],
            "claude_assessment": {
                "status": claude_result["status"],
                "assessment": claude_result["assessment"],
                "recommendation": claude_result["recommendation"],
                "confidence": claude_result["confidence"]
            },
            "gemini_assessment": {
                "status": gemini_result["status"],
                "assessment": gemini_result["assessment"],
                "recommendation": gemini_result["recommendation"],
                "confidence": gemini_result["confidence"],
                "available": gemini_result.get("available", False)
            }
        }
    }


# ── Backward-compatible wrappers ──────────────────────────────────────────────

def generate_recommendation(player, today_data, history,
                            psychology_data=None, nutrition_data=None,
                            upcoming_schedule=None, data_dir=None):
    """Drop-in replacement — uses multi-agent debate automatically"""
    return generate_debate_recommendation(
        player=player,
        today_data=today_data,
        history=history,
        psychology_data=psychology_data,
        nutrition_data=nutrition_data,
        upcoming_schedule=upcoming_schedule,
        data_dir=data_dir
    )


def generate_morning_briefing(players_data):
    """Morning briefing for all players"""
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
            key=lambda x: {"RED": 0, "AMBER": 1, "GREEN": 2, "ERROR": 3}.get(
                x["status"], 4)
        )
    }


# ── Test runner ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from pathlib import Path

    data_dir = Path(__file__).parent.parent.parent / "data" / "synthetic"

    print("=" * 60)
    print("Orbis AI — Multi-Agent Debate Engine Test")
    print("=" * 60)

    with open(data_dir / "player_profile.json") as f:
        player = json.load(f)
    with open(data_dir / "whoop_recovery.json") as f:
        whoop = json.load(f)
    with open(data_dir / "match_results.json") as f:
        matches = json.load(f)
    with open(data_dir / "psychology.json") as f:
        psych = json.load(f)
    with open(data_dir / "nutrition.json") as f:
        nutrition = json.load(f)

    today = whoop[-1].copy()
    if matches:
        lm = matches[-1]
        today.update({
            "match_played": True,
            "match_result": lm["result"],
            "match_score": lm["score"]
        })

    result = generate_debate_recommendation(
        player=player,
        today_data=today,
        history=whoop[-14:],
        psychology_data=psych[-1] if psych else None,
        nutrition_data=nutrition[-2] if len(nutrition) >= 2 else None,
        upcoming_schedule={
            "today": "Technical session — serve mechanics",
            "tomorrow": "Physical conditioning",
            "next_match": "Club tournament Saturday 10am"
        },
        data_dir=str(data_dir)
    )

    print(f"\n{result['status_emoji']} FINAL STATUS: {result['status']}")
    print(f"\n📌 KEY FINDING:\n   {result['key_finding']}")
    print(f"\n🎾 TODAY:\n   {result['today_recommendation']}")
    print(f"\n🔗 CROSS-DATA INSIGHT:\n   {result['cross_data_insight']}")
    print(f"\n👀 WATCH THIS WEEK:\n   {result['watch_this_week']}")

    debate = result.get("debate", {})
    print(f"\n{'='*60}")
    print(f"🤝 AGENT CONSENSUS: {debate.get('agent_consensus','?')}")
    print(f"📊 CONFIDENCE: {debate.get('confidence_level','?')}")
    print(f"⚠️  DISAGREEMENTS: {debate.get('disagreement_flags','NONE')}")
    print(f"🤖 AGENTS USED: {', '.join(debate.get('agents_used',[]))}")

    print(f"\n--- Claude said ({debate.get('claude_assessment',{}).get('status','?')}):")
    print(f"   {debate.get('claude_assessment',{}).get('assessment','')[:200]}")
    print(f"\n--- Gemini said ({debate.get('gemini_assessment',{}).get('status','?')}):")
    print(f"   {debate.get('gemini_assessment',{}).get('assessment','')[:200]}")
