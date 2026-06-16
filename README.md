# 🎾 TennisIQ MVP

> AI-powered player intelligence platform for tennis academies.
> Aggregates Whoop, match results, psychology assessments, and nutrition logs.
> Generates one clear AI coaching recommendation per player per day.

---

## Architecture

```
DATA SOURCES                    YOUR PLATFORM
─────────────                   ─────────────
Whoop API (real)   ──┐
Synthetic data     ──┼──► Data Pipeline ──► PostgreSQL ──► AI Engine ──► Coach Dashboard
Match results      ──┤         │                              (Claude)
Psychology APSQ    ──┤    (normalize all                         │
Nutrition logs     ──┘     into one schema)              Recommendation
                                                         per player/day
```

---

## Quick Start (15 minutes)

### 1. Install dependencies
```bash
cd tennisiq_mvp
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment
```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY at minimum
```

Get your Anthropic key at: https://console.anthropic.com

### 3. Generate Fernando's synthetic data
```bash
python scripts/generate_synthetic_data.py
```

This creates 90 days of realistic data in `data/synthetic/`:
- `player_profile.json` — Fernando's profile
- `whoop_recovery.json` — Daily recovery, HRV, sleep, strain
- `match_results.json` — Match W/L cross-referenced with recovery
- `psychology.json` — Weekly APSQ assessments
- `nutrition.json` — Daily macros and hydration logs
- `benchmarks.json` — ATP stats for reference (Jeff Sackmann dataset)

### 4. Run the API
```bash
python src/main.py
```

Open: http://localhost:8000/dashboard

### 5. Test the AI recommendation
```bash
python src/ai/recommendation_engine.py
```

---

## Connect Your Real Whoop Account

```bash
# Step 1: Register your app at developer.whoop.com
# Set redirect URI: http://localhost:8000/auth/whoop/callback

# Step 2: Add to .env
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret

# Step 3: Get your access token
python src/connectors/whoop_connector.py --auth
# Follow the OAuth flow in your browser
# Copy the access token to .env:
# WHOOP_ACCESS_TOKEN=your_token_here

# Step 4: Your real data now flows into the platform
# The recommendation engine automatically uses real data over synthetic
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Welcome page |
| `/health` | GET | System health check |
| `/dashboard` | GET | Coach dashboard (HTML) |
| `/api/player/FER_001` | GET | Player profile |
| `/api/player/FER_001/recovery?days=14` | GET | Recovery history |
| `/api/player/FER_001/matches?limit=10` | GET | Match results |
| `/api/player/FER_001/psychology?weeks=4` | GET | Psychology assessments |
| `/api/player/FER_001/nutrition?days=7` | GET | Nutrition logs |
| `/api/recommendation/FER_001` | GET | **Generate AI recommendation** |
| `/api/briefing/morning` | GET | All players morning briefing |
| `/api/log/match` | POST | Log a match result manually |
| `/api/log/psychology` | POST | Log a psychology assessment |
| `/api/log/nutrition` | POST | Log nutrition data |
| `/docs` | GET | Auto-generated API docs (Swagger) |

---

## Data Sources Used

### Real (connect via API)
| Source | Data | API | Cost |
|---|---|---|---|
| **Whoop** | Recovery, HRV, sleep, strain | developer.whoop.com | Free dev tier |
| **Terra API** | Unified wearable connector | tryterra.co | Free ≤100 users |
| **ITF** | Tournament results, rankings | On request | Free research |

### Synthetic (generated for MVP)
| Source | Data | Generation |
|---|---|---|
| **Whoop simulation** | 90 days recovery data | `scripts/generate_synthetic_data.py` |
| **Match results** | W/L cross-ref with recovery | Auto-generated |
| **Psychology (APSQ)** | Weekly 10-item assessments | Validated questionnaire |
| **Nutrition logs** | Daily macros + hydration | Sports nutrition guidelines |

### Public Datasets (for benchmarking)
| Source | Data | License |
|---|---|---|
| **Jeff Sackmann ATP** | ATP match stats, rankings | CC BY-NC-SA 4.0 |
| **Match Charting Project** | Point-by-point pro match data | CC BY-NC-SA 4.0 |
| **josedv82/public_sport_science** | Tennis player tracking data | Various |

---

## Psychology Module — APSQ

The Athlete Psychological Strain Questionnaire (APSQ) is a validated
10-item screening tool for athletes. Each question scored 1-5 (lower=better).

**The 10 questions:**
1. Performance worry
2. Concentration difficulties
3. Confidence issues
4. Irritability
5. Sleep worry
6. Loss of motivation
7. External coping (substance use risk)
8. Mental fatigue
9. Reduced enjoyment
10. Pressure management

**Scoring:**
- Average < 2.0 → LOW strain
- Average 2.0-3.0 → MODERATE strain
- Average > 3.0 → ELEVATED strain (flag for professional support)

*Source: Rice et al. (2020). Taylor & Francis. Cronbach α = 0.81-0.84*

---

## Nutrition Module

Targets for Fernando (35yo, 78kg, active tennis player):
- Rest days: 2,400-2,800 kcal
- Training days: 2,900-3,700 kcal
- Match days: 3,300-3,900 kcal
- Protein target: ~2.0g/kg = 156g/day
- Hydration: 2.4-3.2L/day (more on match/physical days)

---

## Upgrade Path: From Synthetic → Real Academy Tools

When you have a pilot academy with Catapult or VALD:

```python
# Replace Whoop connector with Catapult connector
# Same schema — just swap the data source

from src.connectors.catapult_connector import CatapultConnector
# Catapult Connect API: catapult.com/blog/connect-api-integration-ams

from src.connectors.vald_connector import VALDConnector
# VALD Hub API: valdperformance.com/developers
```

The AI engine and dashboard do not change.
Only the data connectors are swapped.

---

## Project Structure

```
tennisiq_mvp/
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── README.md
│
├── data/
│   ├── raw/                  # Raw API responses (not committed)
│   ├── processed/            # Cleaned data
│   └── synthetic/            # Fernando's generated data
│       ├── player_profile.json
│       ├── whoop_recovery.json
│       ├── match_results.json
│       ├── psychology.json
│       ├── nutrition.json
│       └── benchmarks.json
│
├── scripts/
│   └── generate_synthetic_data.py   # Run first
│
└── src/
    ├── main.py                       # FastAPI app (entry point)
    ├── connectors/
    │   └── whoop_connector.py        # Whoop API integration
    └── ai/
        └── recommendation_engine.py  # Claude AI layer
```

---

## Cost to Run

| Item | Cost/month |
|---|---|
| Anthropic API (30 recs/day) | ~€3-5 |
| Hosting (Railway) | €5-10 |
| Terra API (free tier) | €0 |
| Whoop API | €0 |
| **Total** | **~€10-15** |

---

## Next Steps After MVP

1. Connect real Whoop account → replace synthetic recovery data
2. Sign first pilot academy → add their players as profiles
3. Apply to Catapult Connect partner program → replace synthetic strain data
4. Apply to VALD Hub API → add physical test results
5. Build Playtomic integration → real match data
6. Hire technical co-founder → scale infrastructure
# TennisIQ MVP - AI Tennis Academy Platform
