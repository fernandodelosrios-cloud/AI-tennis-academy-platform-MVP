"""
TennisIQ MVP — Whoop API Connector
====================================
Pulls real recovery data from your Whoop account via the Whoop API.
Normalizes into TennisIQ unified schema.

Docs: https://developer.whoop.com/api
Auth: OAuth 2.0 — user authenticates once via browser flow
"""

import os
import httpx
from datetime import date, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

WHOOP_BASE_URL = "https://api.prod.whoop.com/developer/v1"


class WhoopConnector:
    """
    Connects to the Whoop API and pulls Fernando's real recovery data.

    SETUP STEPS:
    1. Go to https://developer.whoop.com
    2. Create an app — set redirect URI to http://localhost:8000/auth/whoop/callback
    3. Copy CLIENT_ID and CLIENT_SECRET to your .env
    4. Run the OAuth flow once: python src/connectors/whoop_connector.py --auth
    5. Copy the access token to WHOOP_ACCESS_TOKEN in .env
    """

    def __init__(self):
        self.client_id = os.getenv("WHOOP_CLIENT_ID")
        self.client_secret = os.getenv("WHOOP_CLIENT_SECRET")
        self.access_token = os.getenv("WHOOP_ACCESS_TOKEN")

        if not self.access_token:
            print("⚠️  No Whoop access token found. Using synthetic data.")
            print("   To connect your real Whoop account:")
            print("   1. Register at developer.whoop.com")
            print("   2. Add WHOOP_ACCESS_TOKEN to your .env file")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get_recovery(self, start_date: date, end_date: date) -> list:
        """Pull daily recovery scores from Whoop"""
        if not self.access_token:
            return []

        with httpx.Client() as client:
            response = client.get(
                f"{WHOOP_BASE_URL}/recovery",
                headers=self._headers(),
                params={
                    "start": f"{start_date}T00:00:00.000Z",
                    "end": f"{end_date}T23:59:59.000Z",
                    "limit": 90
                }
            )

            if response.status_code != 200:
                print(f"⚠️  Whoop API error: {response.status_code}")
                return []

            data = response.json()
            return [self._normalize_recovery(r) for r in data.get("records", [])]

    def get_sleep(self, start_date: date, end_date: date) -> list:
        """Pull sleep performance data from Whoop"""
        if not self.access_token:
            return []

        with httpx.Client() as client:
            response = client.get(
                f"{WHOOP_BASE_URL}/activity/sleep",
                headers=self._headers(),
                params={
                    "start": f"{start_date}T00:00:00.000Z",
                    "end": f"{end_date}T23:59:59.000Z",
                    "limit": 90
                }
            )

            if response.status_code != 200:
                return []

            data = response.json()
            return [self._normalize_sleep(s) for s in data.get("records", [])]

    def get_strain(self, start_date: date, end_date: date) -> list:
        """Pull daily strain data from Whoop"""
        if not self.access_token:
            return []

        with httpx.Client() as client:
            response = client.get(
                f"{WHOOP_BASE_URL}/cycle",
                headers=self._headers(),
                params={
                    "start": f"{start_date}T00:00:00.000Z",
                    "end": f"{end_date}T23:59:59.000Z",
                    "limit": 90
                }
            )

            if response.status_code != 200:
                return []

            data = response.json()
            return [self._normalize_strain(c) for c in data.get("records", [])]

    def get_daily_summary(self, target_date: date) -> dict:
        """Get all Whoop data for a single day — merged into unified schema"""
        recovery = self.get_recovery(target_date, target_date)
        sleep = self.get_sleep(target_date, target_date)
        strain = self.get_strain(target_date, target_date)

        summary = {
            "source": "whoop_api",
            "date": str(target_date),
            "recovery_score": None,
            "hrv_ms": None,
            "sleep_hours": None,
            "sleep_quality": None,
            "resting_hr_bpm": None,
            "strain_score": None,
        }

        if recovery:
            summary.update(recovery[0])
        if sleep:
            s = sleep[0]
            summary["sleep_hours"] = s.get("sleep_hours")
            summary["sleep_quality"] = s.get("sleep_quality")
        if strain:
            summary["strain_score"] = strain[0].get("strain_score")

        return summary

    def _normalize_recovery(self, record: dict) -> dict:
        """Map Whoop recovery response to TennisIQ schema"""
        score = record.get("score", {})
        return {
            "date": record.get("created_at", "")[:10],
            "recovery_score": score.get("recovery_score"),
            "hrv_ms": score.get("hrv_rmssd_milli"),
            "resting_hr_bpm": score.get("resting_heart_rate"),
            "source": "whoop"
        }

    def _normalize_sleep(self, record: dict) -> dict:
        """Map Whoop sleep response to TennisIQ schema"""
        score = record.get("score", {})
        stage_summary = record.get("score", {}).get("stage_summary", {})
        total_ms = stage_summary.get("total_in_bed_time_milli", 0)
        total_hours = round(total_ms / 3_600_000, 1) if total_ms else None

        return {
            "date": record.get("created_at", "")[:10],
            "sleep_hours": total_hours,
            "sleep_quality": score.get("sleep_performance_percentage"),
            "source": "whoop"
        }

    def _normalize_strain(self, record: dict) -> dict:
        """Map Whoop cycle response to TennisIQ schema"""
        score = record.get("score", {})
        return {
            "date": record.get("created_at", "")[:10],
            "strain_score": score.get("strain"),
            "avg_hr_bpm": score.get("average_heart_rate"),
            "max_hr_bpm": score.get("max_heart_rate"),
            "kilojoule": score.get("kilojoule"),
            "source": "whoop"
        }


# ── OAuth flow helper (run once to get access token) ─────────────────────────
def get_auth_url() -> str:
    """Generate the Whoop OAuth authorization URL"""
    client_id = os.getenv("WHOOP_CLIENT_ID", "YOUR_CLIENT_ID")
    redirect_uri = "http://localhost:8000/auth/whoop/callback"
    scopes = "read:recovery read:sleep read:workout read:cycles read:body_measurement"

    return (
        f"https://api.prod.whoop.com/oauth/oauth2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes.replace(' ', '%20')}"
    )


if __name__ == "__main__":
    import sys

    if "--auth" in sys.argv:
        print("\n🔐 WHOOP AUTHENTICATION SETUP")
        print("=" * 50)
        print("1. Open this URL in your browser:")
        print(f"\n   {get_auth_url()}\n")
        print("2. Log in with your Whoop account")
        print("3. Copy the 'code' parameter from the redirect URL")
        print("4. Paste it below to exchange for an access token")
        code = input("\nEnter the authorization code: ").strip()
        print(f"\n✅ Code received. Exchange it at the /auth/whoop/callback endpoint")
        print("   Or use Postman to POST to https://api.prod.whoop.com/oauth/oauth2/token")
    else:
        # Test connection
        connector = WhoopConnector()
        if connector.access_token:
            today = date.today()
            last_week = today - timedelta(days=7)
            print(f"🔄 Fetching Whoop data for last 7 days...")
            recovery = connector.get_recovery(last_week, today)
            print(f"✅ Retrieved {len(recovery)} recovery records")
            if recovery:
                print(f"   Latest: {recovery[-1]}")
        else:
            print("⚠️  Run with --auth flag to set up Whoop connection")
            print("   For now, using synthetic data from scripts/generate_synthetic_data.py")
