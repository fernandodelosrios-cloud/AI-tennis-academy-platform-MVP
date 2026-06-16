"""
TennisIQ MVP — FastAPI Backend
================================
The REST API that powers the coach dashboard.
Handles data ingestion, player management, and recommendation retrieval.

Run: uvicorn src.main:app --reload --port 8000
Docs: http://localhost:8000/docs (auto-generated Swagger UI)
"""

import os
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Import our modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.ai.recommendation_engine import generate_recommendation, generate_morning_briefing
from src.connectors.whoop_connector import WhoopConnector

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TennisIQ MVP API",
    description="AI-powered player intelligence platform for tennis academies",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Data loading (synthetic for MVP) ──────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data" / "synthetic"


def load_synthetic_data():
    """Load Fernando's synthetic data — used when real APIs are not connected"""
    try:
        with open(DATA_DIR / "player_profile.json") as f:
            player = json.load(f)
        with open(DATA_DIR / "whoop_recovery.json") as f:
            whoop = json.load(f)
        with open(DATA_DIR / "match_results.json") as f:
            matches = json.load(f)
        with open(DATA_DIR / "psychology.json") as f:
            psych = json.load(f)
        with open(DATA_DIR / "nutrition.json") as f:
            nutrition = json.load(f)
        return player, whoop, matches, psych, nutrition
    except FileNotFoundError:
        return None, [], [], [], []


# ── Pydantic models ───────────────────────────────────────────────────────────

class MatchLogEntry(BaseModel):
    player_id: str
    date: str
    opponent: str
    result: str          # "W" or "L"
    score: str           # "6-3 7-5"
    surface: str
    duration_minutes: int
    physical_feeling: int  # 1-10

class PsychAssessment(BaseModel):
    player_id: str
    week_date: str
    q1_performance_worry: float
    q2_concentration: float
    q3_confidence: float
    q4_irritability: float
    q5_sleep_worry: float
    q6_motivation: float
    q7_external_coping: float
    q8_fatigue_mental: float
    q9_enjoyment: float
    q10_pressure: float
    coach_notes: str = ""
    pre_match_anxiety: float = 5.0
    self_talk_quality: float = 5.0
    goal_clarity: float = 5.0

class NutritionLog(BaseModel):
    player_id: str
    date: str
    total_calories_kcal: int
    protein_g: int
    carbohydrates_g: int
    fat_g: int
    hydration_liters: float
    pre_training_meal: str = ""
    post_training_meal: str = ""
    notes: str = ""

class UpcomingSchedule(BaseModel):
    today: str = "Training session"
    tomorrow: str = "TBD"
    next_match: str = "No match scheduled"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html><body style="font-family:sans-serif;padding:40px;background:#1c1c1e;color:#f5f2ec">
    <h1 style="color:#e07a5f">🎾 TennisIQ MVP</h1>
    <p>AI-powered player intelligence for tennis academies</p>
    <p><a href="/docs" style="color:#e07a5f">📖 API Documentation</a></p>
    <p><a href="/dashboard" style="color:#e07a5f">📊 Coach Dashboard</a></p>
    <p><a href="/api/recommendation/FER_001" style="color:#e07a5f">🤖 Fernando's Recommendation (test)</a></p>
    </body></html>
    """

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "anthropic_connected": bool(os.getenv("ANTHROPIC_API_KEY")),
        "whoop_connected": bool(os.getenv("WHOOP_ACCESS_TOKEN")),
        "synthetic_data_available": DATA_DIR.exists()
    }


# ── Player endpoints ──────────────────────────────────────────────────────────

@app.get("/api/player/{player_id}")
async def get_player(player_id: str):
    """Get player profile"""
    player, _, _, _, _ = load_synthetic_data()
    if not player or player.get("player_id") != player_id:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@app.get("/api/player/{player_id}/recovery")
async def get_recovery(player_id: str, days: int = 14):
    """Get recovery history for a player"""
    _, whoop, _, _, _ = load_synthetic_data()

    # Try real Whoop first
    whoop_connector = WhoopConnector()
    if whoop_connector.access_token:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        real_data = whoop_connector.get_recovery(start_date, end_date)
        if real_data:
            return {"source": "whoop_api", "data": real_data[-days:]}

    # Fall back to synthetic
    return {
        "source": "synthetic",
        "data": [d for d in whoop if d["player_id"] == player_id][-days:]
    }

@app.get("/api/player/{player_id}/matches")
async def get_matches(player_id: str, limit: int = 10):
    """Get match results for a player"""
    _, _, matches, _, _ = load_synthetic_data()
    player_matches = [m for m in matches if m["player_id"] == player_id]
    return {
        "total": len(player_matches),
        "data": player_matches[-limit:]
    }

@app.get("/api/player/{player_id}/psychology")
async def get_psychology(player_id: str, weeks: int = 4):
    """Get psychology assessment history"""
    _, _, _, psych, _ = load_synthetic_data()
    player_psych = [p for p in psych if p["player_id"] == player_id]
    return {
        "total_assessments": len(player_psych),
        "data": player_psych[-weeks:]
    }

@app.get("/api/player/{player_id}/nutrition")
async def get_nutrition(player_id: str, days: int = 7):
    """Get nutrition log history"""
    _, _, _, _, nutrition = load_synthetic_data()
    player_nutrition = [n for n in nutrition if n["player_id"] == player_id]
    return {
        "total": len(player_nutrition),
        "data": player_nutrition[-days:]
    }


# ── Data ingestion endpoints ──────────────────────────────────────────────────

@app.post("/api/log/match")
async def log_match(entry: MatchLogEntry):
    """Log a match result manually"""
    # In production: save to PostgreSQL
    # For MVP: append to JSON file
    matches_file = DATA_DIR / "match_results.json"
    try:
        with open(matches_file) as f:
            matches = json.load(f)
    except FileNotFoundError:
        matches = []

    new_match = entry.dict()
    new_match["match_id"] = f"M{str(len(matches)+1).zfill(3)}_manual"
    new_match["source"] = "manual_entry"
    matches.append(new_match)

    with open(matches_file, "w") as f:
        json.dump(matches, f, indent=2)

    return {"status": "success", "match_id": new_match["match_id"]}

@app.post("/api/log/psychology")
async def log_psychology(assessment: PsychAssessment):
    """Log a weekly psychology assessment (APSQ)"""
    scores = {
        k: v for k, v in assessment.dict().items()
        if k.startswith("q") and "_" in k[:3]
    }
    apsq_scores = list(scores.values())
    apsq_avg = round(sum(apsq_scores) / len(apsq_scores), 2) if apsq_scores else 0
    strain_level = "LOW" if apsq_avg < 2.0 else "MODERATE" if apsq_avg < 3.0 else "ELEVATED"

    record = {
        **assessment.dict(),
        "apsq_average": apsq_avg,
        "strain_level": strain_level,
        "source": "manual_entry"
    }

    psych_file = DATA_DIR / "psychology.json"
    try:
        with open(psych_file) as f:
            psych_data = json.load(f)
    except FileNotFoundError:
        psych_data = []

    psych_data.append(record)
    with open(psych_file, "w") as f:
        json.dump(psych_data, f, indent=2)

    return {"status": "success", "strain_level": strain_level, "apsq_average": apsq_avg}

@app.post("/api/log/nutrition")
async def log_nutrition(log: NutritionLog):
    """Log daily nutrition"""
    nutrition_file = DATA_DIR / "nutrition.json"
    try:
        with open(nutrition_file) as f:
            nutrition_data = json.load(f)
    except FileNotFoundError:
        nutrition_data = []

    record = {**log.dict(), "source": "manual_entry"}
    nutrition_data.append(record)
    with open(nutrition_file, "w") as f:
        json.dump(nutrition_data, f, indent=2)

    return {"status": "success"}


# ── AI Recommendation endpoints ───────────────────────────────────────────────

@app.get("/api/recommendation/{player_id}")
async def get_recommendation(player_id: str):
    """
    Generate today's AI recommendation for a player.
    Aggregates all available data sources and calls Claude.
    """
    player, whoop_data, matches, psych_data, nutrition_data = load_synthetic_data()

    if not player:
        raise HTTPException(status_code=404, detail="No data found. Run: python scripts/generate_synthetic_data.py")

    # Get today's data (last record)
    player_whoop = [d for d in whoop_data if d["player_id"] == player_id]
    if not player_whoop:
        raise HTTPException(status_code=404, detail="No recovery data found for player")

    today_data = player_whoop[-1].copy()

    # Attach last match result if played recently
    player_matches = [m for m in matches if m["player_id"] == player_id]
    if player_matches:
        last_match = player_matches[-1]
        today_data["match_played"] = True
        today_data["match_result"] = last_match["result"]
        today_data["match_score"] = last_match["score"]

    # Try real Whoop data if connected
    whoop_connector = WhoopConnector()
    if whoop_connector.access_token:
        real_today = whoop_connector.get_daily_summary(date.today())
        if real_today.get("recovery_score"):
            today_data.update({k: v for k, v in real_today.items() if v is not None})
            today_data["source"] = "whoop_api_live"

    # Get history (last 14 days)
    history = player_whoop[-14:]

    # Get latest psychology and nutrition
    player_psych = [p for p in psych_data if p["player_id"] == player_id]
    latest_psych = player_psych[-1] if player_psych else None

    player_nutrition = [n for n in nutrition_data if n["player_id"] == player_id]
    latest_nutrition = player_nutrition[-2] if len(player_nutrition) >= 2 else None

    # Generate recommendation
    recommendation = generate_recommendation(
        player=player,
        today_data=today_data,
        history=history,
        psychology_data=latest_psych,
        nutrition_data=latest_nutrition,
        upcoming_schedule={
            "today": "Training session (confirm with coach)",
            "tomorrow": "TBD",
            "next_match": "See tournament calendar"
        }
    )

    return recommendation


@app.get("/api/briefing/morning")
async def morning_briefing():
    """
    Generate morning briefing for all players in the academy.
    This would be called by the scheduler at 6am daily.
    """
    player, whoop_data, matches, psych_data, nutrition_data = load_synthetic_data()
    if not player:
        raise HTTPException(status_code=404, detail="No data found")

    # For MVP: one player (Fernando)
    players_data = [{
        "player": player,
        "today": whoop_data[-1] if whoop_data else {},
        "history": whoop_data[-14:],
        "psychology": psych_data[-1] if psych_data else None,
        "nutrition": nutrition_data[-2] if len(nutrition_data) >= 2 else None,
        "upcoming": {
            "today": "Training session",
            "tomorrow": "TBD",
            "next_match": "See calendar"
        }
    }]

    briefing = generate_morning_briefing(players_data)
    return briefing


# ── Dashboard endpoint ────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple HTML dashboard for the coach"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TennisIQ — Coach Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #1c1c1e; color: #f5f2ec; min-height: 100vh; }
    .header { background: #2a1510; border-bottom: 2px solid #b84c2c; padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
    .header h1 { font-size: 20px; color: #e07a5f; }
    .header span { font-size: 13px; color: #888; }
    .main { padding: 24px; max-width: 900px; margin: 0 auto; }
    .btn { background: #b84c2c; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; }
    .btn:hover { background: #e07a5f; }
    .btn:disabled { background: #555; cursor: not-allowed; }
    .card { background: #262626; border-radius: 10px; padding: 20px; margin-bottom: 16px; border: 1px solid #333; }
    .card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
    .status-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; letter-spacing: .05em; }
    .GREEN { background: #1a4a2e; color: #4ade80; }
    .AMBER { background: #4a3a0a; color: #fbbf24; }
    .RED { background: #4a1010; color: #f87171; }
    .label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 4px; }
    .value { font-size: 15px; color: #f5f2ec; line-height: 1.5; }
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 12px 0; }
    .metric { background: #1c1c1e; padding: 10px 12px; border-radius: 6px; }
    .metric-val { font-size: 22px; font-weight: 600; color: #e07a5f; }
    .metric-label { font-size: 11px; color: #888; margin-top: 2px; }
    .insight { background: #1a2a3a; border-left: 3px solid #3b82f6; padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 8px 0; }
    .sources { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
    .source-tag { background: #333; color: #aaa; font-size: 10px; padding: 2px 8px; border-radius: 20px; }
    .loading { color: #888; font-style: italic; padding: 20px 0; }
    .section-title { font-size: 13px; font-weight: 600; color: #e07a5f; margin-bottom: 12px; text-transform: uppercase; letter-spacing: .08em; }
  </style>
</head>
<body>
  <div class="header">
    <span>🎾</span>
    <h1>TennisIQ</h1>
    <span>AI Player Intelligence — MVP Demo</span>
  </div>
  <div class="main">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <div class="section-title">Morning Briefing</div>
      <button class="btn" id="refreshBtn" onclick="loadRecommendation()">Generate Recommendation</button>
    </div>

    <div id="playerCard" class="card" style="display:none">
      <div class="card-header">
        <div id="statusEmoji" style="font-size:24px">⚪</div>
        <div>
          <div style="font-size:16px;font-weight:600" id="playerName">—</div>
          <span class="status-badge" id="statusBadge">—</span>
        </div>
        <div style="margin-left:auto;font-size:12px;color:#888" id="genDate">—</div>
      </div>

      <div class="metrics" id="metricsGrid"></div>

      <div class="label" style="margin-top:12px">Key Finding</div>
      <div class="value" id="keyFinding">—</div>

      <div class="label" style="margin-top:12px">Today's Recommendation</div>
      <div class="value" id="todayRec">—</div>

      <div class="insight" id="crossDataDiv" style="display:none">
        <div class="label">Cross-Data Insight 🔗</div>
        <div class="value" id="crossData">—</div>
      </div>

      <div class="label" style="margin-top:12px">Watch This Week 👀</div>
      <div class="value" id="watchWeek">—</div>

      <div class="sources" id="sources"></div>
    </div>

    <div id="loadingMsg" class="loading" style="display:none">🔄 Aggregating data sources and generating AI recommendation...</div>
    <div id="errorMsg" style="display:none;color:#f87171;padding:12px"></div>
  </div>

  <script>
    async function loadRecommendation() {
      const btn = document.getElementById('refreshBtn');
      btn.disabled = true;
      btn.textContent = 'Generating...';
      document.getElementById('playerCard').style.display = 'none';
      document.getElementById('loadingMsg').style.display = 'block';
      document.getElementById('errorMsg').style.display = 'none';

      try {
        const res = await fetch('/api/recommendation/FER_001');
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'API error');
        }
        const data = await res.json();

        // Populate card
        document.getElementById('playerName').textContent = data.player_name || 'Fernando';
        document.getElementById('statusEmoji').textContent = data.status_emoji || '⚪';
        const badge = document.getElementById('statusBadge');
        badge.textContent = data.status;
        badge.className = 'status-badge ' + data.status;
        document.getElementById('genDate').textContent = 'Generated: ' + (data.generated_at || 'now');
        document.getElementById('keyFinding').textContent = data.key_finding || '—';
        let rec = data.today_recommendation || '—'; if(rec.startsWith("'S RECOMMENDATION:")) rec = rec.replace("'S RECOMMENDATION:", '').trim(); document.getElementById('todayRec').textContent = rec;
        document.getElementById('watchWeek').textContent = data.watch_this_week || '—';

        if (data.cross_data_insight) {
          document.getElementById('crossData').textContent = data.cross_data_insight;
          document.getElementById('crossDataDiv').style.display = 'block';
        }

        // Sources
        const srcDiv = document.getElementById('sources');
        srcDiv.innerHTML = (data.data_sources_used || []).map(s =>
          '<span class="source-tag">' + s + '</span>'
        ).join('');

        document.getElementById('loadingMsg').style.display = 'none';
        document.getElementById('playerCard').style.display = 'block';
      } catch (err) {
        document.getElementById('loadingMsg').style.display = 'none';
        document.getElementById('errorMsg').style.display = 'block';
        document.getElementById('errorMsg').textContent = '⚠️ ' + err.message + 
          ' — Make sure to run: python scripts/generate_synthetic_data.py first';
      }

      btn.disabled = false;
      btn.textContent = 'Refresh';
    }
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)

from mangum import Mangum
handler = Mangum(app)


@app.get("/auth/whoop/callback")
async def whoop_callback(code: str):
    """Handle Whoop OAuth callback and exchange code for access token"""
    import httpx
    
    response = httpx.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": os.getenv("WHOOP_CLIENT_ID"),
            "client_secret": os.getenv("WHOOP_CLIENT_SECRET"),
            "redirect_uri": "https://ai-tennis-academy-platform-mvp.vercel.app/auth/whoop/callback"
        }
    )
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        return {
            "status": "success",
            "message": "Copy this access token to your WHOOP_ACCESS_TOKEN environment variable",
            "access_token": access_token,
            "expires_in": token_data.get("expires_in"),
            "refresh_token": token_data.get("refresh_token")
        }
    else:
        return {
            "status": "error",
            "detail": response.text
        }