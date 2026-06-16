"""
TennisIQ MVP — Synthetic Data Generator
========================================
Creates Fernando's player profile + 90 days of realistic synthetic data
combining Whoop-style recovery data, tennis match results, psychology
assessments, and nutrition logs.

Run: python scripts/generate_synthetic_data.py
"""

import json
import random
import math
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

# ── Fernando's Player Profile ─────────────────────────────────────────────────
FERNANDO_PROFILE = {
    "player_id": "FER_001",
    "name": "Fernando",
    "age": 35,
    "nationality": "Peruvian",
    "height_cm": 178,
    "weight_kg": 78,
    "dominant_hand": "right",
    "preferred_surface": "clay",
    "itf_ranking": None,           # recreational/ex-college level
    "level": "advanced_recreational",
    "academy": "TennisIQ Pilot Academy",
    "coach": "Coach Pending",
    "whoop_user_id": "WHOOP_FER_001",  # maps to your real Whoop account
    "created_at": str(date.today())
}

# ── Helper: realistic HRV baseline for a 35yo fit male ───────────────────────
# Typical range: 35-85ms. Fernando baseline ~58ms
def base_hrv():
    return random.gauss(58, 8)

def base_recovery():
    return min(100, max(20, random.gauss(72, 12)))

def base_sleep():
    return round(random.gauss(7.1, 0.8), 1)

def base_resting_hr():
    return int(random.gauss(52, 4))

def strain_from_session(session_type):
    strain_map = {
        "rest": random.gauss(3.2, 0.8),
        "technical": random.gauss(9.5, 1.5),
        "physical": random.gauss(14.2, 2.0),
        "match": random.gauss(15.8, 2.5),
        "match_competitive": random.gauss(17.5, 2.0),
        "recovery": random.gauss(6.5, 1.2),
    }
    return round(max(0, min(21, strain_map.get(session_type, 10.0))), 1)

# ── Generate 90 days of training + recovery data ─────────────────────────────
def generate_whoop_data(player_id: str, days: int = 90) -> list:
    """Simulate Whoop-style daily recovery data"""
    records = []
    base_date = date.today() - timedelta(days=days)

    # Simulate a training block: hard weeks followed by easier weeks
    for i in range(days):
        current_date = base_date + timedelta(days=i)
        week = i // 7
        day_of_week = i % 7  # 0=Mon, 6=Sun

        # Training periodization: week 3 of every 4 is hard
        training_block = week % 4
        if training_block == 2:      # hard week
            fatigue_factor = random.gauss(0.85, 0.06)
        elif training_block == 3:    # recovery week
            fatigue_factor = random.gauss(1.05, 0.04)
        else:                         # normal weeks
            fatigue_factor = random.gauss(0.95, 0.05)

        # Sleep quality slightly worse after matches or hard sessions
        yesterday_was_match = i > 0 and records[-1].get("match_played")
        sleep_penalty = -0.7 if yesterday_was_match else 0

        hrv = round(base_hrv() * fatigue_factor, 1)
        recovery = round(base_recovery() * fatigue_factor, 0)
        sleep_h = round(base_sleep() + sleep_penalty, 1)
        sleep_h = max(4.5, min(10.0, sleep_h))

        # Session type by day of week + block
        if day_of_week == 6:  # Sunday — rest
            session_type = "rest"
        elif day_of_week == 3 and training_block != 2:  # Wednesday lighter
            session_type = "technical"
        elif training_block == 3:  # recovery week
            session_type = random.choice(["technical", "recovery"])
        else:
            session_type = random.choice([
                "technical", "technical",
                "physical", "physical",
                "match", "match_competitive"
            ])

        # Random matches on certain days (not Sunday, not recovery week)
        match_played = (
            session_type in ["match", "match_competitive"] and
            training_block != 3 and
            day_of_week not in [0, 6]
        )

        record = {
            "player_id": player_id,
            "date": str(current_date),
            "recovery_score": int(max(15, min(99, recovery))),
            "hrv_ms": max(20.0, min(120.0, hrv)),
            "sleep_hours": sleep_h,
            "sleep_quality": int(min(100, max(30, recovery * random.gauss(1.0, 0.05)))),
            "resting_hr_bpm": int(base_resting_hr() / fatigue_factor),
            "strain_score": strain_from_session(session_type),
            "session_type": session_type,
            "session_rpe": random.randint(4, 9) if session_type != "rest" else 0,
            "session_minutes": {
                "rest": 0,
                "recovery": 45,
                "technical": random.randint(60, 90),
                "physical": random.randint(75, 105),
                "match": random.randint(70, 100),
                "match_competitive": random.randint(80, 120),
            }.get(session_type, 60),
            "match_played": match_played,
        }
        records.append(record)

    return records

# ── Generate match results ────────────────────────────────────────────────────
def generate_match_results(whoop_data: list) -> list:
    """
    Generate match results for days where match_played=True.
    Cross-references Whoop recovery on match day to influence result.
    """
    matches = []
    match_num = 1

    opponents = [
        "Carlos M.", "Diego R.", "Marcos P.", "Alejandro V.",
        "Juan C.", "Ricardo B.", "Sebastian T.", "Pablo F.",
        "Andres L.", "Miguel A.", "Roberto S.", "Felipe N."
    ]
    surfaces = ["clay", "clay", "clay", "hard", "hard", "indoor_hard"]
    venues = [
        "Real Club de Tenis de la Salud, Seville",
        "Club de Tenis Chamartín, Madrid",
        "Real Club de Tenis Barcelona",
        "Club de Tenis Puerta de Hierro, Madrid",
        "Club de Tenis Valencia",
        "Club de Campo Villa de Madrid",
    ]

    for day_data in whoop_data:
        if not day_data.get("match_played"):
            continue

        recovery = day_data["recovery_score"]

        # Higher recovery = higher win probability
        # Fernando is a good player but recreational — baseline win rate ~55%
        if recovery >= 80:
            win_prob = 0.68
        elif recovery >= 65:
            win_prob = 0.55
        elif recovery >= 50:
            win_prob = 0.42
        else:
            win_prob = 0.28  # tired = more likely to lose

        won = random.random() < win_prob

        # Generate score
        if won:
            set1 = f"6-{random.choice([0,1,2,3,4])}"
            set2 = f"6-{random.choice([0,1,2,3,4,7])}" if random.random() > 0.3 else f"{random.choice([4,5,6])}-6"
            if "6" not in set2.split("-")[0]:
                set3 = f"6-{random.choice([2,3,4])}"
                score = f"{set1} {set2} {set3}"
            else:
                score = f"{set1} {set2}"
        else:
            set1 = f"{random.choice([0,1,2,3,4])}-6"
            set2 = f"{random.choice([0,1,2,3,4])}-6" if random.random() > 0.3 else f"6-{random.choice([4,5])}"
            if "6" in set2.split("-")[0]:
                set3 = f"{random.choice([2,3,4])}-6"
                score = f"{set1} {set2} {set3}"
            else:
                score = f"{set1} {set2}"

        # Serve performance correlated with recovery
        serve_speed_kmh = int(random.gauss(170 if recovery >= 65 else 158, 8))
        first_serve_pct = round(random.gauss(62 if recovery >= 65 else 54, 6), 1)
        winners = random.randint(8 if recovery >= 65 else 5, 22)
        errors = random.randint(10 if recovery >= 65 else 16, 28)

        match = {
            "match_id": f"M{str(match_num).zfill(3)}",
            "player_id": day_data["player_id"],
            "date": day_data["date"],
            "recovery_on_match_day": recovery,
            "hrv_on_match_day": day_data["hrv_ms"],
            "opponent": random.choice(opponents),
            "result": "W" if won else "L",
            "score": score,
            "surface": random.choice(surfaces),
            "venue": random.choice(venues),
            "duration_minutes": int(random.gauss(85, 20)),
            "serve_speed_1st_kmh": serve_speed_kmh,
            "first_serve_in_pct": first_serve_pct,
            "winners": winners,
            "unforced_errors": errors,
            "net_approaches": random.randint(5, 20),
            "physical_feeling_1_10": max(1, min(10, int(recovery / 10))),
            "notes": ""
        }
        matches.append(match)
        match_num += 1

    return matches

# ── Generate psychology assessments ──────────────────────────────────────────
def generate_psychology_data(player_id: str, days: int = 90) -> list:
    """
    Weekly psychology check-in based on the Athlete Psychological Strain
    Questionnaire (APSQ) — validated 10-item tool.
    Simulated as a weekly Monday check-in.
    """
    records = []
    base_date = date.today() - timedelta(days=days)

    weekly_mood_themes = [
        "Focused and motivated this week",
        "Feeling some pressure before upcoming tournament",
        "Good energy — enjoying training",
        "Mild fatigue but mentally strong",
        "High confidence after last week's win",
        "Struggling with consistency — need to reset",
        "Great week — technique clicking",
        "Pre-competition anxiety manageable",
        "Tired but committed",
        "Strong mental session with coach",
        "Worried about right shoulder",
        "Back to form after rest week",
        "Building momentum"
    ]

    for week in range(days // 7):
        check_date = base_date + timedelta(days=week * 7)
        week_num = week + 1

        # APSQ 10 items (1-5 scale, lower = better mental state)
        # Items oscillate with training blocks
        training_block = week % 4
        if training_block == 2:       # hard week — more strain
            base_strain = random.gauss(2.8, 0.6)
        elif training_block == 3:     # recovery week
            base_strain = random.gauss(1.8, 0.4)
        else:
            base_strain = random.gauss(2.2, 0.5)

        apsq_items = {
            "q1_performance_worry": round(max(1, min(5, base_strain + random.gauss(0, 0.4))), 1),
            "q2_concentration": round(max(1, min(5, base_strain - 0.3 + random.gauss(0, 0.3))), 1),
            "q3_confidence": round(max(1, min(5, base_strain + random.gauss(0, 0.5))), 1),
            "q4_irritability": round(max(1, min(5, base_strain + random.gauss(0, 0.4))), 1),
            "q5_sleep_worry": round(max(1, min(5, base_strain + random.gauss(0.2, 0.4))), 1),
            "q6_motivation": round(max(1, min(5, base_strain - 0.5 + random.gauss(0, 0.3))), 1),
            "q7_external_coping": round(max(1, min(5, base_strain + random.gauss(0, 0.5))), 1),
            "q8_fatigue_mental": round(max(1, min(5, base_strain + random.gauss(0.3, 0.3))), 1),
            "q9_enjoyment": round(max(1, min(5, base_strain - 0.8 + random.gauss(0, 0.3))), 1),
            "q10_pressure": round(max(1, min(5, base_strain + random.gauss(0.2, 0.4))), 1),
        }

        apsq_total = round(sum(apsq_items.values()), 1)
        apsq_avg = round(apsq_total / 10, 2)

        # Risk classification: >3.0 avg = elevated strain
        strain_level = "LOW" if apsq_avg < 2.0 else "MODERATE" if apsq_avg < 3.0 else "ELEVATED"

        record = {
            "player_id": player_id,
            "week": week_num,
            "date": str(check_date),
            "apsq_scores": apsq_items,
            "apsq_total": apsq_total,
            "apsq_average": apsq_avg,
            "strain_level": strain_level,
            "coach_notes": random.choice(weekly_mood_themes),
            "pre_match_anxiety_1_10": round(max(1, min(10, base_strain * 2.2 + random.gauss(0, 0.5))), 1),
            "self_talk_quality_1_10": round(max(1, min(10, (5 - base_strain) * 2 + random.gauss(0, 0.5))), 1),
            "goal_clarity_1_10": round(max(1, min(10, (5 - base_strain + 0.5) * 2 + random.gauss(0, 0.4))), 1),
            "session_type": "weekly_apsq_checkin",
            "assessor": "Self-report via TennisIQ app"
        }
        records.append(record)

    return records

# ── Generate nutrition logs ───────────────────────────────────────────────────
def generate_nutrition_data(player_id: str, whoop_data: list) -> list:
    """
    Daily nutrition log for an active 35yo male tennis player.
    Total daily calories: 2,800-3,800 depending on session type.
    Based on sports nutrition guidelines for recreational-competitive athletes.
    """
    records = []

    calorie_targets = {
        "rest": (2400, 2800),
        "recovery": (2600, 3000),
        "technical": (2900, 3300),
        "physical": (3200, 3700),
        "match": (3300, 3800),
        "match_competitive": (3400, 3900),
    }

    for day_data in whoop_data:
        session = day_data.get("session_type", "technical")
        cal_range = calorie_targets.get(session, (2800, 3200))
        total_cal = random.randint(*cal_range)

        # Macro split: ~25% protein, 55% carbs, 20% fat (tennis player ratio)
        protein_g = round(total_cal * 0.25 / 4)   # 4 kcal/g
        carbs_g = round(total_cal * 0.55 / 4)     # 4 kcal/g
        fat_g = round(total_cal * 0.20 / 9)       # 9 kcal/g

        # Hydration — more on heavy training days
        hydration_l = round(random.gauss(
            3.2 if session in ["match", "match_competitive", "physical"] else 2.4,
            0.4
        ), 1)
        hydration_l = max(1.5, min(5.5, hydration_l))

        # Recovery nutrition flag
        post_match_protein = (
            protein_g >= 150 and
            day_data.get("match_played") or session == "physical"
        )

        record = {
            "player_id": player_id,
            "date": day_data["date"],
            "session_type": session,
            "total_calories_kcal": total_cal,
            "protein_g": protein_g,
            "carbohydrates_g": carbs_g,
            "fat_g": fat_g,
            "hydration_liters": hydration_l,
            "pre_training_meal": random.choice([
                "Oats with banana and honey",
                "Toast with eggs and avocado",
                "Rice with chicken",
                "Pasta with olive oil",
                "Yogurt with granola and fruit"
            ]) if session != "rest" else "Light breakfast",
            "post_training_meal": random.choice([
                "Chicken breast with quinoa and vegetables",
                "Salmon with sweet potato",
                "Turkey sandwich with salad",
                "Protein shake + rice cakes",
                "Grilled fish with roasted vegetables"
            ]) if session != "rest" else "Normal lunch",
            "supplements": random.choice([
                ["creatine_5g", "vitamin_d_2000iu", "omega3_1g"],
                ["vitamin_d_2000iu", "magnesium_400mg"],
                ["creatine_5g", "vitamin_d_2000iu"],
                ["vitamin_d_2000iu", "omega3_1g", "magnesium_400mg"],
            ]),
            "recovery_nutrition_adequate": post_match_protein,
            "notes": ""
        }
        records.append(record)

    return records

# ── Pull real Jeff Sackmann ATP match statistics for benchmarking ─────────────
def generate_benchmark_stats() -> dict:
    """
    Reference statistics from Jeff Sackmann's ATP dataset for benchmarking
    Fernando's performance against club-level baseline.
    Source: github.com/JeffSackmann/tennis_atp (CC BY-NC-SA 4.0)
    We use aggregate tour-level stats as a directional benchmark only.
    """
    return {
        "source": "Jeff Sackmann / Tennis Abstract (CC BY-NC-SA 4.0)",
        "level": "ATP Tour reference (directional only)",
        "note": "Fernando is advanced recreational — these are aspirational benchmarks",
        "atp_avg_first_serve_pct": 63.0,
        "atp_avg_serve_speed_1st_kmh": 196,
        "atp_avg_winners_per_match": 28,
        "atp_avg_unforced_errors_per_match": 22,
        "recreational_advanced_benchmark": {
            "first_serve_pct": 58.0,
            "serve_speed_1st_kmh": 165,
            "winners_per_match": 14,
            "unforced_errors_per_match": 20,
            "win_rate_vs_similar_level": 0.50
        }
    }

# ── Main generation function ──────────────────────────────────────────────────
def generate_all_data():
    output_dir = Path(__file__).parent.parent / "data" / "synthetic"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🎾 TennisIQ MVP — Generating Fernando's synthetic data...")
    print("=" * 60)

    # 1. Player profile
    print("📋 Creating Fernando's player profile...")
    with open(output_dir / "player_profile.json", "w") as f:
        json.dump(FERNANDO_PROFILE, f, indent=2)
    print(f"   ✅ Profile saved")

    # 2. Whoop recovery data (90 days)
    print("💪 Generating 90 days of Whoop recovery data...")
    whoop_data = generate_whoop_data("FER_001", days=90)
    with open(output_dir / "whoop_recovery.json", "w") as f:
        json.dump(whoop_data, f, indent=2)
    print(f"   ✅ {len(whoop_data)} daily records generated")

    # 3. Match results (derived from whoop data)
    print("🏆 Generating match results (cross-referenced with recovery)...")
    matches = generate_match_results(whoop_data)
    with open(output_dir / "match_results.json", "w") as f:
        json.dump(matches, f, indent=2)
    wins = sum(1 for m in matches if m["result"] == "W")
    print(f"   ✅ {len(matches)} matches | {wins}W-{len(matches)-wins}L | Win rate: {wins/len(matches)*100:.0f}%")

    # 4. Psychology assessments (weekly)
    print("🧠 Generating weekly psychology assessments (APSQ)...")
    psych_data = generate_psychology_data("FER_001", days=90)
    with open(output_dir / "psychology.json", "w") as f:
        json.dump(psych_data, f, indent=2)
    elevated = sum(1 for p in psych_data if p["strain_level"] == "ELEVATED")
    print(f"   ✅ {len(psych_data)} weekly assessments | {elevated} elevated strain weeks")

    # 5. Nutrition logs
    print("🥗 Generating daily nutrition logs...")
    nutrition = generate_nutrition_data("FER_001", whoop_data)
    with open(output_dir / "nutrition.json", "w") as f:
        json.dump(nutrition, f, indent=2)
    avg_cal = sum(n["total_calories_kcal"] for n in nutrition) / len(nutrition)
    print(f"   ✅ {len(nutrition)} daily logs | Avg {avg_cal:.0f} kcal/day")

    # 6. Benchmark stats
    print("📊 Saving benchmark statistics from Jeff Sackmann ATP dataset...")
    benchmarks = generate_benchmark_stats()
    with open(output_dir / "benchmarks.json", "w") as f:
        json.dump(benchmarks, f, indent=2)
    print(f"   ✅ Benchmarks saved")

    # 7. Summary stats
    print("\n" + "=" * 60)
    print("📈 DATA SUMMARY FOR FERNANDO")
    print("=" * 60)
    print(f"Period: {whoop_data[0]['date']} → {whoop_data[-1]['date']}")
    avg_recovery = sum(d["recovery_score"] for d in whoop_data) / len(whoop_data)
    avg_hrv = sum(d["hrv_ms"] for d in whoop_data) / len(whoop_data)
    avg_sleep = sum(d["sleep_hours"] for d in whoop_data) / len(whoop_data)
    print(f"Avg Recovery: {avg_recovery:.0f}% | Avg HRV: {avg_hrv:.1f}ms | Avg Sleep: {avg_sleep:.1f}h")
    print(f"Matches played: {len(matches)} | Win rate: {wins/len(matches)*100:.0f}%")
    avg_apsq = sum(p["apsq_average"] for p in psych_data) / len(psych_data)
    print(f"Avg APSQ strain: {avg_apsq:.2f}/5.0 (lower=better)")
    print(f"\n✅ All data saved to: {output_dir}")
    print("\n🚀 Next step: Run 'python src/pipeline/load_to_db.py' to load into PostgreSQL")

if __name__ == "__main__":
    generate_all_data()
