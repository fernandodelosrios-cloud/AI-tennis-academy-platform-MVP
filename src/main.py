# -*- coding: utf-8 -*-
"""
TennisIQ MVP — FastAPI Backend v2
"""

import os
import json
from datetime import date, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

load_dotenv()

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.ai.recommendation_engine import generate_recommendation, generate_morning_briefing
from src.connectors.whoop_connector import WhoopConnector

app = FastAPI(title="TennisIQ MVP API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "traceback": traceback.format_exc()}
    )                   

DATA_DIR = Path(__file__).parent.parent / "data" / "synthetic"

DASHBOARD_HTML_CONTENT = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>Orbis AI — Coach Dashboard</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">\n<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>\n<style>\n*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n\n:root {\n  --navy:      #1a2744;\n  --navy-mid:  #243258;\n  --navy-soft: #2d3d6b;\n  --lime:      #a8d130;\n  --lime-dark: #7fa020;\n  --lime-pale: #eef6cc;\n  --bg:        #f0f2f7;\n  --surface:   #ffffff;\n  --surface2:  #f7f8fc;\n  --border:    #e2e6ef;\n  --text:      #1a2744;\n  --text-2:    #4a5577;\n  --text-3:    #8a93aa;\n  --green:     #16a34a;\n  --green-bg:  #dcfce7;\n  --amber:     #d97706;\n  --amber-bg:  #fef3c7;\n  --red:       #dc2626;\n  --red-bg:    #fee2e2;\n  --radius:    10px;\n  --shadow:    0 1px 4px rgba(26,39,68,.08), 0 4px 16px rgba(26,39,68,.06);\n  --shadow-sm: 0 1px 3px rgba(26,39,68,.06);\n}\n\nbody {\n  background: var(--bg);\n  color: var(--text);\n  font-family: \'DM Sans\', system-ui, sans-serif;\n  min-height: 100vh;\n  font-size: 14px;\n  -webkit-font-smoothing: antialiased;\n}\n\n/* ── Header ──────────────────────────────── */\n.header {\n  background: var(--navy);\n  padding: 0 28px;\n  height: 58px;\n  display: flex;\n  align-items: center;\n  justify-content: space-between;\n  position: sticky;\n  top: 0;\n  z-index: 100;\n  box-shadow: 0 2px 12px rgba(26,39,68,.25);\n}\n\n.logo {\n  display: flex;\n  align-items: center;\n  gap: 12px;\n}\n\n/* SVG logo inline */\n.logo-mark {\n  width: 32px;\n  height: 32px;\n  flex-shrink: 0;\n}\n\n.logo-wordmark {\n  display: flex;\n  flex-direction: column;\n  gap: 1px;\n}\n\n.logo-name {\n  font-size: 17px;\n  font-weight: 700;\n  color: #ffffff;\n  letter-spacing: -.01em;\n  line-height: 1;\n}\n.logo-name span { color: var(--lime); }\n\n.logo-tagline {\n  font-size: 9px;\n  color: rgba(255,255,255,.45);\n  letter-spacing: .15em;\n  text-transform: uppercase;\n  font-weight: 500;\n}\n\n.header-right {\n  display: flex;\n  align-items: center;\n  gap: 12px;\n}\n\n.date-chip {\n  font-size: 12px;\n  color: rgba(255,255,255,.55);\n  background: rgba(255,255,255,.08);\n  padding: 5px 12px;\n  border-radius: 20px;\n  border: 1px solid rgba(255,255,255,.12);\n}\n\n.btn-briefing {\n  background: var(--lime);\n  color: var(--navy);\n  border: none;\n  padding: 8px 20px;\n  border-radius: 6px;\n  font-size: 13px;\n  font-weight: 700;\n  cursor: pointer;\n  transition: background .15s, transform .1s;\n  letter-spacing: -.01em;\n}\n.btn-briefing:hover { background: #bde040; }\n.btn-briefing:active { transform: scale(.98); }\n.btn-briefing:disabled { opacity: .5; cursor: not-allowed; transform: none; }\n\n/* ── Main layout ─────────────────────────── */\n.main {\n  max-width: 1280px;\n  margin: 0 auto;\n  padding: 24px 24px 48px;\n}\n\n/* ── Player card ─────────────────────────── */\n.player-card {\n  background: var(--navy);\n  border-radius: var(--radius);\n  padding: 20px 24px;\n  margin-bottom: 20px;\n  display: flex;\n  align-items: center;\n  gap: 20px;\n  box-shadow: var(--shadow);\n  border-left: 4px solid var(--lime);\n}\n\n.player-avatar {\n  width: 52px; height: 52px;\n  border-radius: 50%;\n  background: var(--navy-soft);\n  border: 2px solid var(--lime);\n  display: flex; align-items: center; justify-content: center;\n  font-size: 20px;\n  flex-shrink: 0;\n  color: var(--lime);\n  font-weight: 700;\n  font-family: \'DM Mono\', monospace;\n}\n\n.player-info { flex: 1; }\n.player-name {\n  font-size: 18px; font-weight: 700; color: #fff;\n  letter-spacing: -.02em;\n}\n.player-meta { font-size: 12px; color: rgba(255,255,255,.5); margin-top: 2px; }\n\n.status-pill {\n  display: flex; align-items: center; gap: 6px;\n  padding: 6px 14px;\n  border-radius: 20px;\n  font-size: 12px; font-weight: 700;\n  letter-spacing: .04em; text-transform: uppercase;\n}\n.status-pill.GREEN { background: var(--green-bg); color: var(--green); }\n.status-pill.AMBER { background: var(--amber-bg); color: var(--amber); }\n.status-pill.RED   { background: var(--red-bg);   color: var(--red);   }\n\n.status-dot {\n  width: 7px; height: 7px; border-radius: 50%;\n}\n.GREEN .status-dot { background: var(--green); }\n.AMBER .status-dot { background: var(--amber); }\n.RED   .status-dot { background: var(--red);   }\n\n.gen-label { font-size: 11px; color: rgba(255,255,255,.3); }\n\n/* ── Section grid ────────────────────────── */\n.grid-2 {\n  display: grid;\n  grid-template-columns: 1fr 1fr;\n  gap: 16px;\n  margin-bottom: 16px;\n}\n.grid-full { margin-bottom: 16px; }\n\n@media (max-width: 900px) {\n  .grid-2 { grid-template-columns: 1fr; }\n}\n\n/* ── Cards ───────────────────────────────── */\n.card {\n  background: var(--surface);\n  border-radius: var(--radius);\n  box-shadow: var(--shadow);\n  overflow: hidden;\n  border: 1px solid var(--border);\n}\n\n.card-header {\n  padding: 12px 18px;\n  border-bottom: 1px solid var(--border);\n  display: flex;\n  align-items: center;\n  justify-content: space-between;\n}\n\n.card-title {\n  display: flex;\n  align-items: center;\n  gap: 8px;\n  font-size: 11px;\n  font-weight: 700;\n  text-transform: uppercase;\n  letter-spacing: .1em;\n  color: var(--navy);\n}\n\n.card-title-icon {\n  width: 24px; height: 24px;\n  background: var(--lime-pale);\n  border-radius: 6px;\n  display: flex; align-items: center; justify-content: center;\n  font-size: 12px;\n}\n\n.card-badge {\n  font-size: 10px;\n  font-weight: 600;\n  padding: 2px 8px;\n  border-radius: 20px;\n  background: var(--lime-pale);\n  color: var(--lime-dark);\n  letter-spacing: .04em;\n}\n\n.card-body { padding: 18px; }\n\n/* ── Metric trio ─────────────────────────── */\n.metric-trio {\n  display: grid;\n  grid-template-columns: repeat(3, 1fr);\n  gap: 10px;\n  margin-bottom: 16px;\n}\n\n.metric-box {\n  background: var(--surface2);\n  border: 1px solid var(--border);\n  border-radius: 8px;\n  padding: 12px 14px;\n  position: relative;\n  overflow: hidden;\n}\n.metric-box::before {\n  content: \'\';\n  position: absolute;\n  top: 0; left: 0;\n  width: 3px; height: 100%;\n  background: var(--lime);\n}\n\n.metric-val {\n  font-size: 26px;\n  font-weight: 700;\n  line-height: 1;\n  font-family: \'DM Mono\', monospace;\n  letter-spacing: -.02em;\n  color: var(--navy);\n}\n.metric-val.good { color: var(--green); }\n.metric-val.warn { color: var(--amber); }\n.metric-val.bad  { color: var(--red);   }\n.metric-label {\n  font-size: 10px;\n  color: var(--text-3);\n  margin-top: 4px;\n  font-weight: 600;\n  text-transform: uppercase;\n  letter-spacing: .07em;\n}\n.metric-sub {\n  font-size: 10px;\n  color: var(--text-3);\n  margin-top: 1px;\n}\n\n/* ── Chart container ─────────────────────── */\n.chart-wrap { position: relative; height: 120px; }\n.chart-label {\n  font-size: 10px;\n  color: var(--text-3);\n  text-transform: uppercase;\n  letter-spacing: .08em;\n  font-weight: 600;\n  margin-bottom: 8px;\n}\n\n/* ── Comparison bars ─────────────────────── */\n.bench-section { margin-top: 16px; }\n.bench-label-row {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n  margin-bottom: 10px;\n}\n.bench-title {\n  font-size: 10px;\n  font-weight: 700;\n  text-transform: uppercase;\n  letter-spacing: .08em;\n  color: var(--text-3);\n}\n.bench-legend {\n  display: flex; gap: 12px;\n  font-size: 10px; color: var(--text-3);\n}\n.bench-legend span {\n  display: flex; align-items: center; gap: 4px;\n}\n.ldot {\n  width: 8px; height: 8px;\n  border-radius: 50%;\n  display: inline-block;\n}\n\n.cmp-row {\n  display: grid;\n  grid-template-columns: 100px 1fr 64px;\n  align-items: center;\n  gap: 10px;\n  margin-bottom: 8px;\n}\n.cmp-label { font-size: 11px; color: var(--text-2); }\n.cmp-track {\n  height: 8px;\n  background: var(--border);\n  border-radius: 4px;\n  position: relative;\n  overflow: hidden;\n}\n.cmp-bar-you {\n  height: 100%;\n  background: var(--navy);\n  border-radius: 4px;\n  transition: width .9s cubic-bezier(.16,1,.3,1);\n}\n.cmp-bar-atp {\n  position: absolute;\n  top: 0;\n  height: 100%;\n  background: var(--lime);\n  opacity: .7;\n  border-radius: 4px;\n  transition: width .9s cubic-bezier(.16,1,.3,1);\n}\n.cmp-val {\n  font-size: 11px;\n  color: var(--text-2);\n  font-family: \'DM Mono\', monospace;\n  text-align: right;\n  white-space: nowrap;\n}\n\n/* ── APSQ psychology ─────────────────────── */\n.apsq-grid {\n  display: grid;\n  grid-template-columns: 1fr 1fr;\n  gap: 6px;\n  margin-bottom: 14px;\n}\n.apsq-item {\n  display: flex;\n  align-items: center;\n  gap: 8px;\n  padding: 6px 8px;\n  background: var(--surface2);\n  border-radius: 6px;\n  border: 1px solid var(--border);\n}\n.apsq-name { font-size: 10px; color: var(--text-2); width: 80px; flex-shrink: 0; }\n.apsq-bar-wrap {\n  flex: 1;\n  height: 4px;\n  background: var(--border);\n  border-radius: 2px;\n  overflow: hidden;\n}\n.apsq-fill { height: 100%; border-radius: 2px; transition: width .8s ease; }\n.apsq-num {\n  font-size: 11px;\n  font-family: \'DM Mono\', monospace;\n  color: var(--text-2);\n  width: 22px;\n  text-align: right;\n}\n\n.psych-note {\n  background: var(--surface2);\n  border: 1px solid var(--border);\n  border-left: 3px solid var(--navy);\n  border-radius: 0 8px 8px 0;\n  padding: 10px 14px;\n}\n.psych-note-label { font-size: 10px; color: var(--text-3); font-weight: 700; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 4px; }\n.psych-note-text { font-size: 12px; color: var(--text); line-height: 1.5; }\n\n/* ── Court + match ───────────────────────── */\n.match-wrap {\n  display: grid;\n  grid-template-columns: 210px 1fr;\n  gap: 20px;\n  align-items: start;\n}\n\n@media (max-width: 700px) {\n  .match-wrap { grid-template-columns: 1fr; }\n}\n\n.court-container {\n  display: flex;\n  flex-direction: column;\n  align-items: center;\n  gap: 10px;\n}\n.court-title {\n  font-size: 10px; font-weight: 700;\n  text-transform: uppercase; letter-spacing: .1em;\n  color: var(--text-3);\n}\n\n.stat-table { width: 100%; }\n.stat-table-header {\n  display: grid;\n  grid-template-columns: 1fr auto auto;\n  gap: 12px;\n  padding: 6px 0;\n  border-bottom: 2px solid var(--border);\n  margin-bottom: 4px;\n}\n.sth { font-size: 10px; font-weight: 700; text-transform: uppercase;\n        letter-spacing: .08em; color: var(--text-3); }\n.sth:nth-child(2) { color: var(--navy); }\n.sth:nth-child(3) { color: var(--lime-dark); }\n\n.stat-row {\n  display: grid;\n  grid-template-columns: 1fr auto auto;\n  gap: 12px;\n  padding: 8px 0;\n  border-bottom: 1px solid var(--border);\n  align-items: center;\n}\n.stat-row:last-child { border-bottom: none; }\n.sn { font-size: 12px; color: var(--text-2); }\n.sv { font-size: 13px; font-family: \'DM Mono\', monospace; font-weight: 600; color: var(--navy); min-width: 60px; text-align: right; }\n.sb { font-size: 12px; font-family: \'DM Mono\', monospace; color: var(--lime-dark); min-width: 60px; text-align: right; }\n\n.match-mini-chart {\n  margin-top: 14px;\n  background: var(--surface2);\n  border: 1px solid var(--border);\n  border-radius: 8px;\n  padding: 12px 14px;\n}\n.chart-wrap-sm { position: relative; height: 70px; }\n\n/* ── AI Recommendation ───────────────────── */\n.rec-strip {\n  background: var(--navy);\n  border-radius: var(--radius);\n  overflow: hidden;\n  box-shadow: var(--shadow);\n  border-left: 4px solid var(--lime);\n}\n\n.rec-header {\n  padding: 14px 20px;\n  border-bottom: 1px solid rgba(255,255,255,.08);\n  display: flex;\n  align-items: center;\n  justify-content: space-between;\n}\n.rec-header-title {\n  display: flex; align-items: center; gap: 10px;\n  font-size: 11px; font-weight: 700;\n  text-transform: uppercase; letter-spacing: .1em;\n  color: rgba(255,255,255,.7);\n}\n.rec-header-icon {\n  width: 28px; height: 28px;\n  background: var(--lime);\n  border-radius: 6px;\n  display: flex; align-items: center; justify-content: center;\n  font-size: 14px;\n}\n\n.rec-grid {\n  display: grid;\n  grid-template-columns: 1fr 1fr 1fr 1fr;\n  gap: 0;\n}\n\n@media (max-width: 900px) {\n  .rec-grid { grid-template-columns: 1fr 1fr; }\n}\n\n.rec-block {\n  padding: 18px 20px;\n  border-right: 1px solid rgba(255,255,255,.07);\n}\n.rec-block:last-child { border-right: none; }\n.rec-block:nth-child(2) { border-top: none; }\n\n.rec-block-label {\n  font-size: 10px; font-weight: 700;\n  text-transform: uppercase; letter-spacing: .1em;\n  color: var(--lime);\n  margin-bottom: 8px;\n  display: flex; align-items: center; gap: 5px;\n}\n.rec-block-text {\n  font-size: 12px;\n  color: rgba(255,255,255,.8);\n  line-height: 1.6;\n}\n\n.rec-footer {\n  padding: 10px 20px;\n  border-top: 1px solid rgba(255,255,255,.07);\n  display: flex;\n  align-items: center;\n  gap: 8px;\n  flex-wrap: wrap;\n}\n.source-chip {\n  font-size: 10px;\n  padding: 3px 9px;\n  border-radius: 20px;\n  background: rgba(168,209,48,.15);\n  border: 1px solid rgba(168,209,48,.25);\n  color: var(--lime);\n  font-family: \'DM Mono\', monospace;\n  font-weight: 500;\n}\n\n/* ── Loading / error ─────────────────────── */\n.loading {\n  text-align: center;\n  padding: 64px 20px;\n  color: var(--text-3);\n}\n.spinner {\n  width: 28px; height: 28px;\n  border: 2px solid var(--border);\n  border-top-color: var(--navy);\n  border-radius: 50%;\n  animation: spin .7s linear infinite;\n  margin: 0 auto 16px;\n}\n@keyframes spin { to { transform: rotate(360deg); } }\n\n.error-box {\n  background: var(--red-bg);\n  border: 1px solid rgba(220,38,38,.3);\n  border-radius: 8px;\n  padding: 14px 18px;\n  color: var(--red);\n  font-size: 13px;\n}\n</style>\n</head>\n<body>\n\n<!-- ── Header ──────────────────────────────── -->\n\n<!-- Player Selector Screen -->\n<div id="selectorScreen" style="min-height:100vh;background:#f0f2f7;display:flex;flex-direction:column">\n\n  <!-- Academy header -->\n  <div style="background:var(--navy);padding:0 28px;height:58px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 12px rgba(26,39,68,.25)">\n    <div style="display:flex;align-items:center;gap:12px">\n      <svg width="32" height="32" viewBox="0 0 64 64" fill="none">\n        <ellipse cx="30" cy="34" rx="22" ry="22" fill="#a8d130"/>\n        <path d="M12 28 Q22 20 30 34 Q38 48 48 40" stroke="white" stroke-width="3" fill="none" stroke-linecap="round"/>\n        <ellipse cx="34" cy="28" rx="26" ry="14" stroke="#1a2744" stroke-width="2.5" fill="none" transform="rotate(-20 34 28)"/>\n        <circle cx="54" cy="16" r="4" fill="#a8d130"/>\n        <circle cx="44" cy="22" r="2" fill="rgba(255,255,255,.6)"/>\n        <line x1="44" y1="22" x2="54" y2="16" stroke="rgba(255,255,255,.4)" stroke-width="1"/>\n      </svg>\n      <div>\n        <div style="font-size:17px;font-weight:700;color:#fff;letter-spacing:-.01em;line-height:1">Orbis <span style="color:#a8d130">AI</span></div>\n        <div style="font-size:9px;color:rgba(255,255,255,.45);letter-spacing:.15em;text-transform:uppercase;font-weight:500">Data · Insight · Elevate Your Game</div>\n      </div>\n    </div>\n    <div style="font-size:12px;color:rgba(255,255,255,.4)">Roger Lederer Academy</div>\n  </div>\n\n  <!-- Welcome panel -->\n  <div style="flex:1;display:flex;align-items:center;justify-content:center;padding:40px 24px">\n    <div style="width:100%;max-width:680px">\n\n      <!-- Coach greeting -->\n      <div style="text-align:center;margin-bottom:36px">\n        <div style="display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;background:#1a2744;border-radius:50%;border:2px solid #a8d130;font-size:22px;font-weight:700;color:#a8d130;font-family:\'DM Mono\',monospace;margin-bottom:14px">T</div>\n        <div style="font-size:22px;font-weight:700;color:#1a2744;letter-spacing:-.02em">Good morning, Coach Toni</div>\n        <div style="font-size:14px;color:#4a5577;margin-top:6px">Roger Lederer Academy · Select a player to view their morning briefing</div>\n        <div style="font-size:12px;color:#8a93aa;margin-top:4px" id="selectorDate">—</div>\n      </div>\n\n      <!-- Player cards -->\n      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">\n\n        <!-- Fernando — data available -->\n        <div onclick="selectPlayer(\'fernando\')" style="background:#fff;border-radius:12px;border:1.5px solid #a8d130;padding:24px 18px;cursor:pointer;transition:all .15s;box-shadow:0 4px 20px rgba(168,209,48,.15);position:relative;text-align:center"\n             onmouseover="this.style.transform=\'translateY(-3px)\';this.style.boxShadow=\'0 8px 28px rgba(168,209,48,.22)\'"\n             onmouseout="this.style.transform=\'\';this.style.boxShadow=\'0 4px 20px rgba(168,209,48,.15)\'">\n          <!-- Updated badge -->\n          <div style="position:absolute;top:-10px;left:50%;transform:translateX(-50%);background:#a8d130;color:#1a2744;font-size:9px;font-weight:700;padding:3px 10px;border-radius:20px;letter-spacing:.06em;white-space:nowrap">✓ DATA UPDATED</div>\n          <!-- Avatar -->\n          <div style="width:64px;height:64px;border-radius:50%;background:#1a2744;border:3px solid #a8d130;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;color:#a8d130;font-family:\'DM Mono\',monospace;margin:10px auto 14px">F</div>\n          <!-- Name — highlighted -->\n          <div style="font-size:18px;font-weight:700;color:#1a2744;letter-spacing:-.02em">Fernando</div>\n          <div style="font-size:11px;color:#4a5577;margin-top:3px">Advanced recreational</div>\n          <!-- Stats preview -->\n          <div style="margin-top:14px;padding-top:14px;border-top:1px solid #e2e6ef;display:grid;grid-template-columns:1fr 1fr;gap:8px">\n            <div style="text-align:center">\n              <div style="font-size:16px;font-weight:700;color:#16a34a">84%</div>\n              <div style="font-size:9px;color:#8a93aa;text-transform:uppercase;letter-spacing:.06em">Recovery</div>\n            </div>\n            <div style="text-align:center">\n              <div style="font-size:16px;font-weight:700;color:#1a2744">57ms</div>\n              <div style="font-size:9px;color:#8a93aa;text-transform:uppercase;letter-spacing:.06em">HRV</div>\n            </div>\n          </div>\n          <div style="margin-top:12px;background:#1a2744;color:#fff;font-size:12px;font-weight:600;padding:8px;border-radius:6px">View Briefing →</div>\n          <a href="/report/demo" style="display:block;margin-top:6px;background:rgba(168,209,48,.12);border:1px solid rgba(168,209,48,.25);color:#7fa020;font-size:11px;font-weight:600;padding:6px;border-radius:6px;text-decoration:none;text-align:center">📋 Progress Report</a>\n        </div>\n\n        <!-- James — no data -->\n        <div style="background:#fff;border-radius:12px;border:1.5px solid #e2e6ef;padding:24px 18px;text-align:center;opacity:.6;cursor:not-allowed">\n          <div style="width:64px;height:64px;border-radius:50%;background:#f0f2f7;border:3px solid #e2e6ef;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;color:#8a93aa;font-family:\'DM Mono\',monospace;margin:10px auto 14px">J</div>\n          <div style="font-size:18px;font-weight:700;color:#8a93aa;letter-spacing:-.02em">James</div>\n          <div style="font-size:11px;color:#a0a8bb;margin-top:3px">Intermediate</div>\n          <div style="margin-top:14px;padding-top:14px;border-top:1px solid #e2e6ef">\n            <div style="font-size:11px;color:#a0a8bb;padding:8px 0">No data connected yet</div>\n          </div>\n          <div style="margin-top:12px;background:#f0f2f7;color:#a0a8bb;font-size:12px;font-weight:600;padding:8px;border-radius:6px;cursor:not-allowed">Pending setup</div>\n        </div>\n\n        <!-- Jaime — no data -->\n        <div style="background:#fff;border-radius:12px;border:1.5px solid #e2e6ef;padding:24px 18px;text-align:center;opacity:.6;cursor:not-allowed">\n          <div style="width:64px;height:64px;border-radius:50%;background:#f0f2f7;border:3px solid #e2e6ef;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;color:#8a93aa;font-family:\'DM Mono\',monospace;margin:10px auto 14px">J</div>\n          <div style="font-size:18px;font-weight:700;color:#8a93aa;letter-spacing:-.02em">Jaime</div>\n          <div style="font-size:11px;color:#a0a8bb;margin-top:3px">Competitive junior</div>\n          <div style="margin-top:14px;padding-top:14px;border-top:1px solid #e2e6ef">\n            <div style="font-size:11px;color:#a0a8bb;padding:8px 0">No data connected yet</div>\n          </div>\n          <div style="margin-top:12px;background:#f0f2f7;color:#a0a8bb;font-size:12px;font-weight:600;padding:8px;border-radius:6px;cursor:not-allowed">Pending setup</div>\n        </div>\n\n      </div>\n\n      <!-- Academy footer -->\n      <div style="text-align:center;margin-top:28px;font-size:11px;color:#a0a8bb">\n        Roger Lederer Academy · 3 players enrolled · 1 active data connection\n      </div>\n\n    </div>\n  </div>\n</div>\n\n<!-- Main Dashboard (hidden until player selected) -->\n<div id="mainDashboard" style="display:none">\n<header class="header">\n  <div class="logo">\n    <!-- Orbis AI inline SVG logo mark -->\n    <svg class="logo-mark" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">\n      <!-- Tennis ball shape -->\n      <ellipse cx="30" cy="34" rx="22" ry="22" fill="#a8d130"/>\n      <path d="M12 28 Q22 20 30 34 Q38 48 48 40" stroke="white" stroke-width="3" fill="none" stroke-linecap="round"/>\n      <!-- Orbit ring -->\n      <ellipse cx="34" cy="28" rx="26" ry="14" stroke="#1a2744" stroke-width="2.5" fill="none" transform="rotate(-20 34 28)"/>\n      <!-- Data dot -->\n      <circle cx="54" cy="16" r="4" fill="#a8d130"/>\n      <!-- Network dots -->\n      <circle cx="44" cy="22" r="2" fill="rgba(255,255,255,.6)"/>\n      <circle cx="38" cy="18" r="1.5" fill="rgba(255,255,255,.5)"/>\n      <line x1="44" y1="22" x2="54" y2="16" stroke="rgba(255,255,255,.4)" stroke-width="1"/>\n      <line x1="38" y1="18" x2="44" y2="22" stroke="rgba(255,255,255,.3)" stroke-width="1"/>\n    </svg>\n    <div class="logo-wordmark">\n      <div class="logo-name">Orbis <span>AI</span></div>\n      <div class="logo-tagline">Data · Insight · Elevate Your Game</div>\n    </div>\n  </div>\n  <div class="header-right">\n    <div class="date-chip" id="todayDate">—</div>\n    <button class="btn-briefing" id="btnRefresh" onclick="loadAll()">Morning Briefing</button>\n  </div>\n</header>\n\n<!-- ── Main ────────────────────────────────── -->\n<main class="main">\n  <div id="loadingState" class="loading" style="display:none">\n    <div class="spinner"></div>\n    Aggregating data sources and generating AI coaching recommendation…\n  </div>\n  <div id="errorState" class="error-box" style="display:none"></div>\n\n  <div id="content" style="display:none">\n\n    <!-- Player card -->\n    <div class="player-card">\n      <div class="player-avatar" id="playerInitial">F</div>\n      <div class="player-info">\n        <div class="player-name" id="playerName">—</div>\n        <div class="player-meta" id="playerMeta">—</div>\n      </div>\n      <div class="status-pill" id="statusPill">\n        <div class="status-dot"></div>\n        <span id="statusText">—</span>\n      </div>\n      <div class="gen-label" id="genLabel">—</div>\n    </div>\n\n    <!-- Row 1: Physical + Psychology -->\n    <div class="grid-2">\n\n      <!-- Physical Readiness -->\n      <div class="card">\n        <div class="card-header">\n          <div class="card-title">\n            <div class="card-title-icon">💪</div>\n            Physical Readiness\n          </div>\n          <div class="card-badge">WHOOP</div>\n        </div>\n        <div class="card-body">\n          <div class="metric-trio">\n            <div class="metric-box">\n              <div class="metric-val" id="mRec">—</div>\n              <div class="metric-label">Recovery</div>\n              <div class="metric-sub" id="mRecSub">—</div>\n            </div>\n            <div class="metric-box">\n              <div class="metric-val" id="mHRV">—</div>\n              <div class="metric-label">HRV · ms</div>\n              <div class="metric-sub" id="mHRVSub">—</div>\n            </div>\n            <div class="metric-box">\n              <div class="metric-val" id="mSleep">—</div>\n              <div class="metric-label">Sleep · h</div>\n              <div class="metric-sub">Rec: ≥7.0h</div>\n            </div>\n          </div>\n\n          <div class="chart-label">14-day recovery trend</div>\n          <div class="chart-wrap">\n            <canvas id="recoveryChart"></canvas>\n          </div>\n\n          <div class="bench-section">\n            <div class="bench-label-row">\n              <div class="bench-title">vs ATP Benchmarks</div>\n              <div class="bench-legend">\n                <span><span class="ldot" style="background:var(--navy)"></span>Fernando</span>\n                <span><span class="ldot" style="background:var(--lime)"></span>ATP / Benchmark</span>\n              </div>\n            </div>\n            <div class="cmp-row">\n              <div class="cmp-label">First Serve %</div>\n              <div class="cmp-track">\n                <div class="cmp-bar-atp" id="barAtpServe" style="width:0"></div>\n                <div class="cmp-bar-you" id="barYouServe" style="width:0"></div>\n              </div>\n              <div class="cmp-val" id="valServe">—</div>\n            </div>\n            <div class="cmp-row">\n              <div class="cmp-label">Win Rate</div>\n              <div class="cmp-track">\n                <div class="cmp-bar-atp" id="barAtpWin" style="width:50%"></div>\n                <div class="cmp-bar-you" id="barYouWin" style="width:0"></div>\n              </div>\n              <div class="cmp-val" id="valWin">—</div>\n            </div>\n            <div class="cmp-row">\n              <div class="cmp-label">Resting HR</div>\n              <div class="cmp-track">\n                <div class="cmp-bar-atp" style="width:52%"></div>\n                <div class="cmp-bar-you" id="barYouRHR" style="width:0"></div>\n              </div>\n              <div class="cmp-val" id="valRHR">— bpm</div>\n            </div>\n          </div>\n        </div>\n      </div>\n\n      <!-- Psychology -->\n      <div class="card">\n        <div class="card-header">\n          <div class="card-title">\n            <div class="card-title-icon">🧠</div>\n            Psychology · APSQ\n          </div>\n          <div class="card-badge" id="strainBadge">—</div>\n        </div>\n        <div class="card-body">\n          <div class="metric-trio">\n            <div class="metric-box">\n              <div class="metric-val" id="mApsq">—</div>\n              <div class="metric-label">APSQ Score</div>\n              <div class="metric-sub">Lower = better</div>\n            </div>\n            <div class="metric-box">\n              <div class="metric-val" id="mAnxiety">—</div>\n              <div class="metric-label">Pre-match</div>\n              <div class="metric-sub">Anxiety /10</div>\n            </div>\n            <div class="metric-box">\n              <div class="metric-val" id="mSelfTalk">—</div>\n              <div class="metric-label">Self-Talk</div>\n              <div class="metric-sub">Quality /10</div>\n            </div>\n          </div>\n\n          <div class="apsq-grid" id="apsqGrid"></div>\n\n          <div class="psych-note">\n            <div class="psych-note-label">Coach notes</div>\n            <div class="psych-note-text" id="psychNotes">—</div>\n          </div>\n        </div>\n      </div>\n    </div>\n\n    <!-- Row 2: Match Performance -->\n    <div class="grid-full">\n      <div class="card">\n        <div class="card-header">\n          <div class="card-title">\n            <div class="card-title-icon">🏆</div>\n            Match Performance\n          </div>\n          <div class="card-badge" id="matchBadge">—</div>\n        </div>\n        <div class="card-body">\n          <!-- KPI strip -->\n            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px">\n              <div class="metric-box">\n                <div class="metric-val good" id="kpiWinRate">60%</div>\n                <div class="metric-label">Win Rate</div>\n                <div class="metric-sub">vs 50% recreational</div>\n              </div>\n              <div class="metric-box">\n                <div class="metric-val good">75%</div>\n                <div class="metric-label">Win — High Recovery</div>\n                <div class="metric-sub">When recovery ≥80%</div>\n              </div>\n              <div class="metric-box">\n                <div class="metric-val warn">40%</div>\n                <div class="metric-label">Win — Low Recovery</div>\n                <div class="metric-sub">When recovery &lt;65%</div>\n              </div>\n              <div class="metric-box">\n                <div class="metric-val" id="kpiDuration">—</div>\n                <div class="metric-label">Avg Duration</div>\n                <div class="metric-sub">85 min rec. avg</div>\n              </div>\n            </div>\n\n            <!-- Court + Stats -->\n            <div style="display:grid;grid-template-columns:190px 1fr;gap:24px;align-items:start">\n\n              <!-- Court diagram -->\n              <div style="display:flex;flex-direction:column;align-items:center;gap:10px">\n                <div style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:var(--text-3)">Serve zones · deuce</div>\n                <svg width="180" height="300" viewBox="0 0 180 300" xmlns="http://www.w3.org/2000/svg">\n                  <rect width="180" height="300" fill="#2d5a3d" rx="6"/>\n                  <rect x="14" y="14" width="152" height="272" fill="none" stroke="rgba(255,255,255,.75)" stroke-width="1.5"/>\n                  <line x1="90" y1="14" x2="90" y2="286" stroke="rgba(255,255,255,.45)" stroke-width="1"/>\n                  <line x1="14" y1="150" x2="166" y2="150" stroke="rgba(255,255,255,.9)" stroke-width="2"/>\n                  <circle cx="90" cy="150" r="2.5" fill="rgba(255,255,255,.8)"/>\n                  <line x1="14" y1="90" x2="166" y2="90" stroke="rgba(255,255,255,.55)" stroke-width="1.2"/>\n                  <line x1="14" y1="210" x2="166" y2="210" stroke="rgba(255,255,255,.55)" stroke-width="1.2"/>\n                  <rect x="15" y="91" width="50" height="58" fill="rgba(168,209,48,.22)" rx="2"/>\n                  <rect x="65" y="91" width="50" height="58" fill="rgba(168,209,48,.12)" rx="2"/>\n                  <rect x="115" y="91" width="50" height="58" fill="rgba(168,209,48,.35)" rx="2"/>\n                  <text x="40" y="125" fill="rgba(255,255,255,.75)" font-size="11" font-family="-apple-system,sans-serif" font-weight="500" text-anchor="middle">24%</text>\n                  <text x="90" y="125" fill="rgba(255,255,255,.65)" font-size="11" font-family="-apple-system,sans-serif" font-weight="500" text-anchor="middle">18%</text>\n                  <text x="140" y="119" fill="#a8d130" font-size="13" font-family="-apple-system,sans-serif" font-weight="700" text-anchor="middle">58%</text>\n                  <text x="140" y="132" fill="rgba(168,209,48,.7)" font-size="8.5" font-family="-apple-system,sans-serif" text-anchor="middle">1st in</text>\n                  <text x="40" y="87" fill="rgba(255,255,255,.4)" font-size="7.5" font-family="-apple-system,sans-serif" text-anchor="middle" font-weight="600">WIDE</text>\n                  <text x="90" y="87" fill="rgba(255,255,255,.4)" font-size="7.5" font-family="-apple-system,sans-serif" text-anchor="middle" font-weight="600">BODY</text>\n                  <text x="140" y="87" fill="rgba(255,255,255,.4)" font-size="7.5" font-family="-apple-system,sans-serif" text-anchor="middle" font-weight="600">T</text>\n                  <rect x="115" y="154" width="50" height="55" fill="rgba(22,163,74,.2)" rx="2"/>\n                  <text x="140" y="184" fill="rgba(22,163,74,.85)" font-size="9" font-family="-apple-system,sans-serif" font-weight="600" text-anchor="middle">Winners</text>\n                  <rect x="15" y="154" width="72" height="32" fill="rgba(220,38,38,.18)" rx="2"/>\n                  <text x="51" y="173" fill="rgba(220,38,38,.8)" font-size="9" font-family="-apple-system,sans-serif" font-weight="600" text-anchor="middle">Errors</text>\n                  <text x="90" y="10" fill="rgba(255,255,255,.3)" font-size="8" font-family="-apple-system,sans-serif" text-anchor="middle">OPPONENT</text>\n                  <text x="90" y="296" fill="rgba(255,255,255,.3)" font-size="8" font-family="-apple-system,sans-serif" text-anchor="middle">FERNANDO</text>\n                </svg>\n                <div style="font-size:10px;color:var(--text-3);text-align:center;line-height:1.6">\n                  <span style="display:inline-block;width:8px;height:8px;background:rgba(168,209,48,.6);border-radius:1px;margin-right:3px"></span>Serve zones<br>\n                  <span style="display:inline-block;width:8px;height:8px;background:rgba(22,163,74,.4);border-radius:1px;margin-right:3px"></span>Winners&nbsp;&nbsp;\n                  <span style="display:inline-block;width:8px;height:8px;background:rgba(220,38,38,.35);border-radius:1px;margin-right:3px"></span>Errors\n                </div>\n              </div>\n\n              <!-- Stats + chart column -->\n              <div style="display:flex;flex-direction:column;gap:16px">\n\n                <!-- Stat table -->\n                <div>\n                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">\n                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text-3)">Detailed stats</div>\n                    <div style="display:flex;gap:12px;font-size:10px;color:var(--text-3)">\n                      <span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--navy);margin-right:3px"></span>Fernando</span>\n                      <span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--lime);margin-right:3px"></span>ATP benchmark</span>\n                    </div>\n                  </div>\n                  <div class="stat-table">\n                    <div class="stat-table-header">\n                      <div class="sth">Metric</div>\n                      <div class="sth">Fernando</div>\n                      <div class="sth">Benchmark</div>\n                    </div>\n                    <div class="stat-row">\n                      <div class="sn">Matches played</div>\n                      <div class="sv" id="smMatches">—</div>\n                      <div class="sb">—</div>\n                    </div>\n                    <div class="stat-row">\n                      <div class="sn">First serve %</div>\n                      <div class="sv" id="smFirstServe">58%</div>\n                      <div class="sb">63% ATP avg</div>\n                    </div>\n                    <div class="stat-row">\n                      <div class="sn">Winners / match</div>\n                      <div class="sv" id="smWinners">12</div>\n                      <div class="sb">28.4 ATP avg</div>\n                    </div>\n                    <div class="stat-row">\n                      <div class="sn">Unforced errors</div>\n                      <div class="sv" id="smErrors" style="color:var(--amber)">22</div>\n                      <div class="sb">21.8 ATP avg</div>\n                    </div>\n                    <div class="stat-row">\n                      <div class="sn">Avg match duration</div>\n                      <div class="sv" id="smDuration">—</div>\n                      <div class="sb">85 min rec.</div>\n                    </div>\n                    <div class="stat-row">\n                      <div class="sn">Last match</div>\n                      <div class="sv" id="smLast" style="font-size:11px">—</div>\n                      <div class="sb"></div>\n                    </div>\n                  </div>\n                </div>\n\n                <!-- Recovery chart -->\n                <div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px">\n                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">\n                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text-3)">Recovery on match days</div>\n                    <div style="display:flex;gap:10px;font-size:10px;color:var(--text-3)">\n                      <span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#16a34a;margin-right:3px"></span>Win</span>\n                      <span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#dc2626;margin-right:3px"></span>Loss</span>\n                    </div>\n                  </div>\n                  <div class="chart-wrap-sm">\n                    <canvas id="matchChart" role="img" aria-label="Bar chart showing Fernando recovery on match days, green for wins and red for losses">Recovery on match days — wins tend to occur with higher recovery scores.</canvas>\n                  </div>\n                  <!-- Key insight strip -->\n                  <div style="margin-top:12px;padding:10px 12px;background:var(--surface);border-radius:0 6px 6px 0;border-left:3px solid var(--lime);border-top:1px solid var(--border);border-right:1px solid var(--border);border-bottom:1px solid var(--border)">\n                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--lime-dark);margin-bottom:3px">Key pattern</div>\n                    <div style="font-size:12px;color:var(--text-2);line-height:1.5">Fernando wins 75% of matches when recovery ≥80% vs 40% when below 65%. Recovery is the most controllable performance variable.</div>\n                  </div>\n                </div>\n\n              </div>\n            </div>\n        </div>\n      </div>\n    </div>\n\n    <!-- Row 3: AI Recommendation -->\n    <div class="grid-full">\n      <div class="rec-strip">\n        <div class="rec-header">\n          <div class="rec-header-title">\n            <div class="rec-header-icon">🤖</div>\n            AI Coaching Recommendation · Orbis AI\n          </div>\n          <div style="font-size:11px;color:rgba(255,255,255,.3)" id="recModel">—</div>\n        </div>\n        <div class="rec-grid">\n          <div class="rec-block">\n            <div class="rec-block-label">⚡ Key Finding</div>\n            <div class="rec-block-text" id="recKey">—</div>\n          </div>\n          <div class="rec-block">\n            <div class="rec-block-label">🎾 Today\'s Recommendation</div>\n            <div class="rec-block-text" id="recToday">—</div>\n          </div>\n          <div class="rec-block">\n            <div class="rec-block-label">🔗 Cross-Data Insight</div>\n            <div class="rec-block-text" id="recCross">—</div>\n          </div>\n          <div class="rec-block">\n            <div class="rec-block-label">👀 Watch This Week</div>\n            <div class="rec-block-text" id="recWatch">—</div>\n          </div>\n        </div>\n        <div class="rec-footer" id="sourcesRow"></div>\n      </div>\n    </div>\n\n  </div><!-- /content -->\n</main>\n\n<script>\nconst APSQ_LABELS = {\n  q1_performance_worry:\'Performance worry\', q2_concentration:\'Concentration\',\n  q3_confidence:\'Confidence\', q4_irritability:\'Irritability\',\n  q5_sleep_worry:\'Sleep worry\', q6_motivation:\'Motivation\',\n  q7_external_coping:\'External coping\', q8_fatigue_mental:\'Mental fatigue\',\n  q9_enjoyment:\'Enjoyment\', q10_pressure:\'Pressure\'\n};\n\nlet chartR = null, chartM = null;\n\ndocument.getElementById(\'todayDate\').textContent =\n  new Date().toLocaleDateString(\'en-GB\',{weekday:\'short\',day:\'numeric\',month:\'short\',year:\'numeric\'});\n\nfunction rcol(v){ return v>=75?\'#16a34a\':v>=55?\'#d97706\':\'#dc2626\'; }\n\nasync function loadAll(){\n  const btn = document.getElementById(\'btnRefresh\');\n  btn.disabled = true; btn.textContent = \'Loading…\';\n  document.getElementById(\'content\').style.display=\'none\';\n  document.getElementById(\'errorState\').style.display=\'none\';\n  document.getElementById(\'loadingState\').style.display=\'block\';\n\n  try{\n    const [recR,recovR,matchR,psychR] = await Promise.all([\n      fetch(\'/api/recommendation/FER_001\'),\n      fetch(\'/api/player/FER_001/recovery?days=14\'),\n      fetch(\'/api/player/FER_001/matches?limit=10\'),\n      fetch(\'/api/player/FER_001/psychology?weeks=4\'),\n    ]);\n    const rec=await recR.json(), recov=await recovR.json(),\n          matches=await matchR.json(), psych=await psychR.json();\n    render(rec,recov,matches,psych);\n    document.getElementById(\'loadingState\').style.display=\'none\';\n    document.getElementById(\'content\').style.display=\'block\';\n  }catch(e){\n    document.getElementById(\'loadingState\').style.display=\'none\';\n    const el=document.getElementById(\'errorState\');\n    el.style.display=\'block\';\n    el.textContent=\'⚠️ \'+e.message+\' — Run: python scripts/generate_synthetic_data.py\';\n  }\n  btn.disabled=false; btn.textContent=\'Refresh\';\n}\n\nfunction render(rec,recov,matches,psych){\n  // ── Player header\n  const st=rec.status||\'GREEN\';\n  const pill=document.getElementById(\'statusPill\');\n  pill.className=\'status-pill \'+st;\n  document.getElementById(\'statusText\').textContent=st;\n  document.getElementById(\'playerName\').textContent=rec.player_name||\'Fernando\';\n  document.getElementById(\'playerMeta\').textContent=\'Age 35 · Clay specialist · Advanced recreational · Orbis AI pilot\';\n  document.getElementById(\'playerInitial\').textContent=(rec.player_name||\'F\')[0];\n  document.getElementById(\'genLabel\').textContent=\'Generated \'+( rec.generated_at||\'today\');\n\n  // ── Physical\n  const hist=recov.data||[];\n  const td=hist[hist.length-1]||{};\n  const rv=td.recovery_score||0, hv=td.hrv_ms||0, sl=td.sleep_hours||0;\n  const avg7=hist.slice(-7);\n  const avgRv=Math.round(avg7.reduce((a,d)=>a+(d.recovery_score||0),0)/Math.max(avg7.length,1));\n  const avgHrv=Math.round(avg7.reduce((a,d)=>a+(d.hrv_ms||0),0)/Math.max(avg7.length,1));\n\n  const mRec=document.getElementById(\'mRec\');\n  mRec.textContent=rv+\'%\'; mRec.className=\'metric-val \'+(rv>=75?\'good\':rv>=55?\'warn\':\'bad\');\n  document.getElementById(\'mRecSub\').textContent=\'7d avg: \'+avgRv+\'%\';\n\n  const mHRV=document.getElementById(\'mHRV\');\n  mHRV.textContent=Math.round(hv); mHRV.className=\'metric-val \'+(hv>=60?\'good\':hv>=45?\'warn\':\'bad\');\n  document.getElementById(\'mHRVSub\').textContent=\'7d avg: \'+avgHrv+\'ms\';\n\n  const mSl=document.getElementById(\'mSleep\');\n  mSl.textContent=sl.toFixed(1); mSl.className=\'metric-val \'+(sl>=7?\'good\':sl>=6?\'warn\':\'bad\');\n\n  // Recovery chart\n  const labels=hist.map(d=>d.date?d.date.slice(5):\'\');\n  const vals=hist.map(d=>d.recovery_score||0);\n  if(chartR) chartR.destroy();\n  chartR=new Chart(document.getElementById(\'recoveryChart\'),{\n    type:\'bar\',\n    data:{labels,datasets:[{\n      data:vals,\n      backgroundColor:vals.map(v=>rcol(v)+\'33\'),\n      borderColor:vals.map(v=>rcol(v)),\n      borderWidth:1.5, borderRadius:3\n    }]},\n    options:{\n      responsive:true, maintainAspectRatio:false,\n      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.parsed.y+\'% recovery\'}}},\n      scales:{\n        x:{ticks:{color:\'#8a93aa\',font:{size:9}},grid:{display:false},border:{display:false}},\n        y:{min:0,max:100,ticks:{color:\'#8a93aa\',font:{size:9},stepSize:25},\n           grid:{color:\'#e2e6ef\'},border:{display:false}}\n      }\n    }\n  });\n\n  // Benchmarks\n  const mData=matches.data||[];\n  const wins=mData.filter(m=>m.result===\'W\').length;\n  const tot=mData.length||1;\n  const wr=Math.round(wins/tot*100);\n  const rhr=td.resting_hr_bpm||56;\n\n  document.getElementById(\'barAtpServe\').style.width=\'63%\';\n  document.getElementById(\'barYouServe\').style.width=\'58%\';\n  document.getElementById(\'valServe\').textContent=\'58% / 63%\';\n  document.getElementById(\'barYouWin\').style.width=wr+\'%\';\n  document.getElementById(\'valWin\').textContent=wr+\'% / 50%\';\n  document.getElementById(\'barYouRHR\').style.width=Math.min(100,rhr)+\'%\';\n  document.getElementById(\'valRHR\').textContent=rhr+\' / 52 bpm\';\n\n  // ── Psychology\n  const pd=psych.data||[];\n  const lp=pd[pd.length-1]||{};\n  const apsq=lp.apsq_average||0;\n  const strain=lp.strain_level||\'LOW\';\n  const mAp=document.getElementById(\'mApsq\');\n  mAp.textContent=apsq.toFixed(2);\n  mAp.className=\'metric-val \'+(apsq<2?\'good\':apsq<3?\'warn\':\'bad\');\n  const badge=document.getElementById(\'strainBadge\');\n  badge.textContent=strain+\' STRAIN\';\n  badge.style.background=apsq<2?\'#dcfce7\':apsq<3?\'#fef3c7\':\'#fee2e2\';\n  badge.style.color=apsq<2?\'#16a34a\':apsq<3?\'#d97706\':\'#dc2626\';\n\n  const anx=lp.pre_match_anxiety_1_10||0;\n  const st2=lp.self_talk_quality_1_10||0;\n  const mAn=document.getElementById(\'mAnxiety\');\n  mAn.textContent=anx.toFixed(1); mAn.className=\'metric-val \'+(anx<=4?\'good\':anx<=6?\'warn\':\'bad\');\n  const mST=document.getElementById(\'mSelfTalk\');\n  mST.textContent=st2.toFixed(1); mST.className=\'metric-val \'+(st2>=7?\'good\':st2>=5?\'warn\':\'bad\');\n\n  const scores=lp.apsq_scores||{};\n  const grid=document.getElementById(\'apsqGrid\');\n  grid.innerHTML=\'\';\n  Object.entries(APSQ_LABELS).forEach(([k,lbl])=>{\n    const v=scores[k]||0;\n    const pct=(v/5)*100;\n    const col=v<=2?\'#16a34a\':v<=3?\'#d97706\':\'#dc2626\';\n    grid.innerHTML+=`<div class="apsq-item">\n      <div class="apsq-name">${lbl}</div>\n      <div class="apsq-bar-wrap"><div class="apsq-fill" style="width:${pct}%;background:${col}"></div></div>\n      <div class="apsq-num" style="color:${col}">${v.toFixed(1)}</div>\n    </div>`;\n  });\n  document.getElementById(\'psychNotes\').textContent=lp.coach_notes||\'No notes this week.\';\n\n  // ── Match stats\n  const avgDur=mData.length?Math.round(mData.reduce((a,m)=>a+(m.duration_minutes||85),0)/mData.length):85;\n  const lm=mData[mData.length-1];\n  function setEl(id,val){const e=document.getElementById(id);if(e)e.textContent=val;}\n  setEl(\'smMatches\',tot);\n  setEl(\'smWinRate\',wr+\'%\');\n  setEl(\'smDuration\',avgDur+\' min\');\n  setEl(\'kpiWinRate\',wr+\'%\');\n  setEl(\'kpiDuration\',avgDur+\' min\');\n  setEl(\'matchBadge\',wins+\'W-\'+(tot-wins)+\'L\');\n  setEl(\'smLast\',lm?`${lm.result} ${lm.score||\'\'} vs ${lm.opponent||\'—\'}`:\'—\');\n\n  // Match recovery chart\n  const md8=mData.slice(-8);\n  if(chartM) chartM.destroy();\n  chartM=new Chart(document.getElementById(\'matchChart\'),{\n    type:\'bar\',\n    data:{\n      labels:md8.map(m=>m.date?m.date.slice(5):\'\'),\n      datasets:[{\n        data:md8.map(m=>m.recovery_on_match_day||0),\n        backgroundColor:md8.map(m=>m.result===\'W\'?\'rgba(22,163,74,.45)\':\'rgba(220,38,38,.35)\'),\n        borderColor:md8.map(m=>m.result===\'W\'?\'#16a34a\':\'#dc2626\'),\n        borderWidth:1.5, borderRadius:3\n      }]\n    },\n    options:{\n      responsive:true, maintainAspectRatio:false,\n      plugins:{legend:{display:false},tooltip:{callbacks:{\n        label:c=>`${c.parsed.y}% recovery — ${md8[c.dataIndex]?.result===\'W\'?\'WIN\':\'LOSS\'}`\n      }}},\n      scales:{\n        x:{ticks:{color:\'#8a93aa\',font:{size:9}},grid:{display:false},border:{display:false}},\n        y:{min:0,max:100,ticks:{color:\'#8a93aa\',font:{size:9}},\n           grid:{color:\'#e2e6ef\'},border:{display:false}}\n      }\n    }\n  });\n\n  // ── AI Recommendation\n  document.getElementById(\'recKey\').textContent=rec.key_finding||\'—\';\n  document.getElementById(\'recToday\').textContent=rec.today_recommendation||\'—\';\n  document.getElementById(\'recCross\').textContent=rec.cross_data_insight||\'—\';\n  document.getElementById(\'recWatch\').textContent=rec.watch_this_week||\'—\';\n  document.getElementById(\'recModel\').textContent=\'claude-sonnet-4-6 · \'+rec.generated_at;\n  document.getElementById(\'sourcesRow\').innerHTML=\n    (rec.data_sources_used||[]).map(s=>`<span class="source-chip">${s}</span>`).join(\'\');\n}\n\nloadAll();\n</script>\n</div><!-- /mainDashboard -->\n<script>\ndocument.getElementById(\'selectorDate\').textContent =\n  new Date().toLocaleDateString(\'en-GB\',{weekday:\'long\',day:\'numeric\',month:\'long\',year:\'numeric\'});\n\nfunction selectPlayer(id) {\n  if (id !== \'fernando\') return;\n  document.getElementById(\'selectorScreen\').style.display = \'none\';\n  document.getElementById(\'mainDashboard\').style.display = \'block\';\n  loadAll();\n}\n</script>\n</body>\n</html>'


REGISTER_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>Orbis AI — Register</title>\n<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">\n<style>\n:root{--navy:#3d1a6e;--lime:#3ecf7e;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--red:#dc2626;--radius:10px;}\n*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}\nbody{font-family:\'DM Sans\',sans-serif;background:var(--bg);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;}\n.logo{display:flex;align-items:center;gap:10px;margin-bottom:28px;}\n.logo img{height:36px;}\n.logo-text{font-size:20px;font-weight:700;color:var(--navy);}\n.logo-text span{color:var(--lime);}\n.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:32px;width:100%;max-width:440px;box-shadow:0 4px 24px rgba(61,26,110,.08);}\n.card-title{font-size:18px;font-weight:700;color:var(--navy);margin-bottom:4px;}\n.card-sub{font-size:13px;color:var(--text2);margin-bottom:24px;}\n.form-group{margin-bottom:14px;}\n.form-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--text3);margin-bottom:5px;display:block;}\n.form-input{width:100%;border:1px solid var(--border);border-radius:7px;padding:10px 12px;font-size:13px;font-family:inherit;color:var(--text);background:var(--surface);outline:none;transition:border .15s;}\n.form-input:focus{border-color:var(--navy);}\n.form-select{width:100%;border:1px solid var(--border);border-radius:7px;padding:10px 12px;font-size:13px;font-family:inherit;color:var(--text);background:var(--surface);outline:none;cursor:pointer;}\n.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px;}\n.btn{width:100%;background:var(--navy);color:#fff;border:none;border-radius:7px;padding:12px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;margin-top:6px;transition:background .15s;}\n.btn:hover{background:#4a2080;}\n.btn:disabled{opacity:.5;cursor:not-allowed;}\n.divider{display:flex;align-items:center;gap:10px;margin:16px 0;color:var(--text3);font-size:12px;}\n.divider::before,.divider::after{content:\'\';flex:1;height:0.5px;background:var(--border);}\n.link-row{text-align:center;font-size:13px;color:var(--text2);}\n.link-row a{color:var(--navy);font-weight:600;text-decoration:none;}\n.error-box{background:#fee2e2;border:1px solid rgba(220,38,38,.2);border-radius:7px;padding:10px 12px;font-size:12px;color:var(--red);margin-bottom:14px;display:none;}\n.lang-toggle{position:absolute;top:16px;right:16px;display:flex;gap:6px;}\n.lang-btn{background:none;border:1px solid var(--border);border-radius:20px;padding:4px 12px;font-size:11px;cursor:pointer;font-family:inherit;color:var(--text2);}\n.lang-btn.active{background:var(--navy);color:#fff;border-color:var(--navy);}\n.sport-group{display:flex;gap:8px;}\n.sport-btn{flex:1;padding:8px;border:1.5px solid var(--border);border-radius:7px;font-size:12px;font-weight:500;cursor:pointer;font-family:inherit;color:var(--text2);background:var(--surface);transition:all .15s;text-align:center;}\n.sport-btn.selected{border-color:var(--navy);background:#f0ebfa;color:var(--navy);}\n</style>\n</head>\n<body>\n<div style="position:relative;width:100%;max-width:440px">\n  <div class="lang-toggle">\n    <button class="lang-btn active" onclick="setLang(\'en\')" id="btn-en">EN</button>\n    <button class="lang-btn" onclick="setLang(\'es\')" id="btn-es">ES</button>\n  </div>\n</div>\n\n<div class="logo">\n  <svg width="32" height="32" viewBox="0 0 64 64" fill="none">\n    <circle cx="32" cy="32" r="28" fill="none" stroke="#3d1a6e" stroke-width="4"/>\n    <circle cx="32" cy="32" r="19" fill="none" stroke="#3d1a6e" stroke-width="4"/>\n    <circle cx="32" cy="32" r="10" fill="none" stroke="#3d1a6e" stroke-width="4"/>\n    <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>\n  </svg>\n  <div class="logo-text">Orbis <span>AI</span></div>\n</div>\n\n<div class="card">\n  <div class="card-title" id="t-title">Create your coach account</div>\n  <div class="card-sub" id="t-sub">Start your 30-day free trial. No credit card required.</div>\n\n  <div class="error-box" id="errorBox"></div>\n\n  <div class="form-group">\n    <label class="form-label" id="t-name">Full name</label>\n    <input class="form-input" type="text" id="fullName" placeholder="Toni Alcalá">\n  </div>\n\n  <div class="form-group">\n    <label class="form-label" id="t-email">Email</label>\n    <input class="form-input" type="email" id="email" placeholder="toni@academy.com">\n  </div>\n\n  <div class="form-group">\n    <label class="form-label" id="t-password">Password</label>\n    <input class="form-input" type="password" id="password" placeholder="Min. 8 characters">\n  </div>\n\n  <div class="form-group">\n    <label class="form-label" id="t-academy">Academy name</label>\n    <input class="form-input" type="text" id="academyName" placeholder="Roger Lederer Academy">\n  </div>\n\n  <div class="row2">\n    <div class="form-group">\n      <label class="form-label" id="t-city">City</label>\n      <input class="form-input" type="text" id="city" placeholder="Madrid">\n    </div>\n    <div class="form-group">\n      <label class="form-label" id="t-country">Country</label>\n      <select class="form-select" id="country">\n        <option value="Spain">Spain</option>\n        <option value="United Kingdom">United Kingdom</option>\n        <option value="United States">United States</option>\n        <option value="France">France</option>\n        <option value="Italy">Italy</option>\n        <option value="Germany">Germany</option>\n        <option value="Other">Other</option>\n      </select>\n    </div>\n  </div>\n\n  <div class="form-group">\n    <label class="form-label" id="t-sport">Sport</label>\n    <div class="sport-group">\n      <button class="sport-btn selected" onclick="toggleSport(\'tennis\',this)" id="sp-tennis">🎾 Tennis</button>\n      <button class="sport-btn" onclick="toggleSport(\'padel\',this)" id="sp-padel">🏓 Padel</button>\n      <button class="sport-btn" onclick="toggleSport(\'both\',this)" id="sp-both" id="t-both">Both</button>\n    </div>\n  </div>\n\n  <button class="btn" id="registerBtn" onclick="register()" id="t-btn">Create account</button>\n\n  <div class="divider" id="t-or">or</div>\n  <div class="link-row">\n    <span id="t-have">Already have an account?</span>\n    <a href="/login" id="t-signin"> Sign in</a>\n  </div>\n</div>\n\n<script>\nconst SUPABASE_URL = \'__SUPABASE_URL__\';\nconst SUPABASE_KEY = \'__SUPABASE_KEY__\';\nlet selectedSport = \'tennis\';\n\nconst T = {\n  en: {\n    title:\'Create your coach account\', sub:\'Start your 30-day free trial. No credit card required.\',\n    name:\'Full name\', email:\'Email\', password:\'Password\', academy:\'Academy name\',\n    city:\'City\', country:\'Country\', sport:\'Sport\', both:\'Both\',\n    btn:\'Create account\', or:\'or\', have:\'Already have an account?\', signin:\' Sign in\',\n    err_fields:\'Please fill in all fields\', err_pass:\'Password must be at least 8 characters\',\n    success:\'Account created! Redirecting...\'\n  },\n  es: {\n    title:\'Crea tu cuenta de entrenador\', sub:\'Empieza tu prueba gratuita de 30 días. Sin tarjeta de crédito.\',\n    name:\'Nombre completo\', email:\'Correo electrónico\', password:\'Contraseña\', academy:\'Nombre de la academia\',\n    city:\'Ciudad\', country:\'País\', sport:\'Deporte\', both:\'Ambos\',\n    btn:\'Crear cuenta\', or:\'o\', have:\'¿Ya tienes cuenta?\', signin:\' Iniciar sesión\',\n    err_fields:\'Por favor completa todos los campos\', err_pass:\'La contraseña debe tener al menos 8 caracteres\',\n    success:\'¡Cuenta creada! Redirigiendo...\'\n  }\n};\n\nlet lang = \'en\';\nfunction setLang(l) {\n  lang = l;\n  document.getElementById(\'btn-en\').classList.toggle(\'active\', l===\'en\');\n  document.getElementById(\'btn-es\').classList.toggle(\'active\', l===\'es\');\n  const t = T[l];\n  document.getElementById(\'t-title\').textContent = t.title;\n  document.getElementById(\'t-sub\').textContent = t.sub;\n  document.getElementById(\'t-name\').textContent = t.name;\n  document.getElementById(\'t-email\').textContent = t.email;\n  document.getElementById(\'t-password\').textContent = t.password;\n  document.getElementById(\'t-academy\').textContent = t.academy;\n  document.getElementById(\'t-city\').textContent = t.city;\n  document.getElementById(\'t-country\').textContent = t.country;\n  document.getElementById(\'t-sport\').textContent = t.sport;\n  document.getElementById(\'sp-both\').textContent = \'🏓 \' + t.both;\n  document.getElementById(\'registerBtn\').textContent = t.btn;\n  document.getElementById(\'t-or\').textContent = t.or;\n  document.getElementById(\'t-have\').textContent = t.have;\n  document.getElementById(\'t-signin\').textContent = t.signin;\n}\n\nfunction toggleSport(s, btn) {\n  selectedSport = s;\n  document.querySelectorAll(\'.sport-btn\').forEach(b => b.classList.remove(\'selected\'));\n  btn.classList.add(\'selected\');\n}\n\nfunction showError(msg) {\n  const box = document.getElementById(\'errorBox\');\n  box.textContent = msg;\n  box.style.display = \'block\';\n}\n\nasync function register() {\n  const btn = document.getElementById(\'registerBtn\');\n  const t = T[lang];\n  const fullName = document.getElementById(\'fullName\').value.trim();\n  const email = document.getElementById(\'email\').value.trim();\n  const password = document.getElementById(\'password\').value;\n  const academyName = document.getElementById(\'academyName\').value.trim();\n  const city = document.getElementById(\'city\').value.trim();\n  const country = document.getElementById(\'country\').value;\n\n  document.getElementById(\'errorBox\').style.display = \'none\';\n\n  if (!fullName || !email || !password || !academyName || !city) {\n    showError(t.err_fields); return;\n  }\n  if (password.length < 8) {\n    showError(t.err_pass); return;\n  }\n\n  btn.disabled = true;\n  btn.textContent = \'...\';\n\n  try {\n    const res = await fetch(\'/api/auth/register\', {\n      method: \'POST\',\n      headers: {\'Content-Type\': \'application/json\'},\n      body: JSON.stringify({\n        full_name: fullName, email, password,\n        academy_name: academyName, city, country,\n        sport: selectedSport, role: \'coach\'\n      })\n    });\n    const data = await res.json();\n    if (res.ok) {\n      btn.textContent = t.success;\n      setTimeout(() => window.location.href = \'/coach\', 1500);\n    } else {\n      showError(data.detail || \'Registration failed\');\n      btn.disabled = false;\n      btn.textContent = t.btn;\n    }\n  } catch(e) {\n    showError(\'Network error — please try again\');\n    btn.disabled = false;\n    btn.textContent = t.btn;\n  }\n}\n</script>\n</body>\n</html>'

LOGIN_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>Orbis AI — Login</title>\n<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">\n<style>\n:root{--navy:#3d1a6e;--lime:#3ecf7e;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--red:#dc2626;--radius:10px;}\n*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}\nbody{font-family:\'DM Sans\',sans-serif;background:var(--bg);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;}\n.logo{display:flex;align-items:center;gap:10px;margin-bottom:28px;}\n.logo-text{font-size:20px;font-weight:700;color:var(--navy);}\n.logo-text span{color:var(--lime);}\n.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:32px;width:100%;max-width:400px;box-shadow:0 4px 24px rgba(61,26,110,.08);}\n.card-title{font-size:18px;font-weight:700;color:var(--navy);margin-bottom:4px;}\n.card-sub{font-size:13px;color:var(--text2);margin-bottom:24px;}\n.form-group{margin-bottom:14px;}\n.form-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--text3);margin-bottom:5px;display:block;}\n.form-input{width:100%;border:1px solid var(--border);border-radius:7px;padding:10px 12px;font-size:13px;font-family:inherit;color:var(--text);outline:none;transition:border .15s;}\n.form-input:focus{border-color:var(--navy);}\n.btn{width:100%;background:var(--navy);color:#fff;border:none;border-radius:7px;padding:12px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;margin-top:6px;transition:background .15s;}\n.btn:hover{background:#4a2080;}\n.btn:disabled{opacity:.5;cursor:not-allowed;}\n.divider{display:flex;align-items:center;gap:10px;margin:16px 0;color:var(--text3);font-size:12px;}\n.divider::before,.divider::after{content:\'\';flex:1;height:0.5px;background:var(--border);}\n.link-row{text-align:center;font-size:13px;color:var(--text2);}\n.link-row a{color:var(--navy);font-weight:600;text-decoration:none;}\n.error-box{background:#fee2e2;border:1px solid rgba(220,38,38,.2);border-radius:7px;padding:10px 12px;font-size:12px;color:var(--red);margin-bottom:14px;display:none;}\n.demo-link{text-align:center;margin-top:16px;padding-top:16px;border-top:0.5px solid var(--border);font-size:12px;color:var(--text3);}\n.demo-link a{color:var(--lime);font-weight:600;text-decoration:none;}\n.lang-toggle{position:absolute;top:16px;right:16px;display:flex;gap:6px;}\n.lang-btn{background:none;border:1px solid var(--border);border-radius:20px;padding:4px 12px;font-size:11px;cursor:pointer;font-family:inherit;color:var(--text2);}\n.lang-btn.active{background:var(--navy);color:#fff;border-color:var(--navy);}\n</style>\n</head>\n<body>\n<div style="position:relative;width:100%;max-width:400px">\n  <div class="lang-toggle">\n    <button class="lang-btn active" onclick="setLang(\'en\')" id="btn-en">EN</button>\n    <button class="lang-btn" onclick="setLang(\'es\')" id="btn-es">ES</button>\n  </div>\n</div>\n\n<div class="logo">\n  <svg width="32" height="32" viewBox="0 0 64 64" fill="none">\n    <circle cx="32" cy="32" r="28" fill="none" stroke="#3d1a6e" stroke-width="4"/>\n    <circle cx="32" cy="32" r="19" fill="none" stroke="#3d1a6e" stroke-width="4"/>\n    <circle cx="32" cy="32" r="10" fill="none" stroke="#3d1a6e" stroke-width="4"/>\n    <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>\n  </svg>\n  <div class="logo-text">Orbis <span>AI</span></div>\n</div>\n\n<div class="card">\n  <div class="card-title" id="t-title">Welcome back</div>\n  <div class="card-sub" id="t-sub">Sign in to your Orbis AI account</div>\n\n  <div class="error-box" id="errorBox"></div>\n\n  <div class="form-group">\n    <label class="form-label" id="t-email">Email</label>\n    <input class="form-input" type="email" id="email" placeholder="toni@academy.com">\n  </div>\n\n  <div class="form-group">\n    <label class="form-label" id="t-password">Password</label>\n    <input class="form-input" type="password" id="password"\n      onkeydown="if(event.key===\'Enter\')login()">\n  </div>\n\n  <button class="btn" id="loginBtn" onclick="login()" id="t-btn">Sign in</button>\n\n  <div class="divider" id="t-or">or</div>\n  <div class="link-row">\n    <span id="t-new">New coach?</span>\n    <a href="/register" id="t-register"> Create account</a>\n  </div>\n\n  <div class="demo-link">\n    <span id="t-demo">Want to see the demo first?</span>\n    <a href="/dashboard" id="t-demo-link"> View demo →</a>\n  </div>\n</div>\n\n<script>\nconst T = {\n  en: {\n    title:\'Welcome back\', sub:\'Sign in to your Orbis AI account\',\n    email:\'Email\', password:\'Password\', btn:\'Sign in\', or:\'or\',\n    new:\'New coach?\', register:\' Create account\',\n    demo:\'Want to see the demo first?\', demo_link:\' View demo →\',\n    err_fields:\'Please enter your email and password\',\n    err_invalid:\'Invalid email or password\'\n  },\n  es: {\n    title:\'Bienvenido de vuelta\', sub:\'Inicia sesión en tu cuenta Orbis AI\',\n    email:\'Correo electrónico\', password:\'Contraseña\', btn:\'Iniciar sesión\', or:\'o\',\n    new:\'¿Eres nuevo?\', register:\' Crear cuenta\',\n    demo:\'¿Quieres ver el demo primero?\', demo_link:\' Ver demo →\',\n    err_fields:\'Por favor introduce tu correo y contraseña\',\n    err_invalid:\'Correo o contraseña incorrectos\'\n  }\n};\n\nlet lang = \'en\';\nfunction setLang(l) {\n  lang = l;\n  document.getElementById(\'btn-en\').classList.toggle(\'active\', l===\'en\');\n  document.getElementById(\'btn-es\').classList.toggle(\'active\', l===\'es\');\n  const t = T[l];\n  [\'title\',\'sub\',\'email\',\'password\',\'btn\',\'or\',\'new\',\'register\',\'demo\',\'demo_link\'].forEach(k => {\n    const el = document.getElementById(\'t-\'+k);\n    if(el) el.textContent = t[k];\n  });\n}\n\nfunction showError(msg) {\n  const box = document.getElementById(\'errorBox\');\n  box.textContent = msg;\n  box.style.display = \'block\';\n}\n\nasync function login() {\n  const btn = document.getElementById(\'loginBtn\');\n  const t = T[lang];\n  const email = document.getElementById(\'email\').value.trim();\n  const password = document.getElementById(\'password\').value;\n\n  document.getElementById(\'errorBox\').style.display = \'none\';\n  if (!email || !password) { showError(t.err_fields); return; }\n\n  btn.disabled = true; btn.textContent = \'...\';\n\n  try {\n    const res = await fetch(\'/api/auth/login\', {\n      method: \'POST\',\n      headers: {\'Content-Type\':\'application/json\'},\n      body: JSON.stringify({email, password})\n    });\n    const data = await res.json();\n    if (res.ok) {\n      localStorage.setItem(\'orbis_token\', data.access_token);\n      localStorage.setItem(\'orbis_role\', data.role);\n      localStorage.setItem(\'orbis_name\', data.full_name);\n      window.location.href = data.role === \'coach\' ? \'/coach\' : \'/student/dashboard\';\n    } else {\n      showError(t.err_invalid);\n      btn.disabled = false; btn.textContent = t.btn;\n    }\n  } catch(e) {\n    showError(\'Network error — please try again\');\n    btn.disabled = false; btn.textContent = t.btn;\n  }\n}\n</script>\n</body>\n</html>'

COACH_DASHBOARD_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>Orbis AI — Coach Dashboard</title>\n<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">\n<style>\n:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--green:#16a34a;--amber:#d97706;--red:#dc2626;--radius:10px;--shadow:0 1px 4px rgba(61,26,110,.08),0 4px 16px rgba(61,26,110,.06);}\n*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}\nbody{font-family:\'DM Sans\',sans-serif;background:var(--bg);color:var(--text);font-size:14px;}\n.header{background:var(--navy);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;box-shadow:0 2px 12px rgba(61,26,110,.25);position:sticky;top:0;z-index:100;}\n.logo{display:flex;align-items:center;gap:10px;}\n.logo-text{font-size:15px;font-weight:700;color:#fff;}\n.logo-text span{color:var(--lime);}\n.logo-sub{font-size:9px;color:rgba(255,255,255,.4);letter-spacing:.14em;text-transform:uppercase;margin-top:1px;}\n.header-right{display:flex;align-items:center;gap:10px;}\n.coach-chip{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);border-radius:20px;padding:4px 12px;font-size:12px;color:rgba(255,255,255,.8);}\n.btn-logout{background:none;border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.6);border-radius:6px;padding:5px 12px;font-size:11px;cursor:pointer;font-family:inherit;}\n.lang-btn-sm{background:none;border:none;color:rgba(255,255,255,.4);font-size:11px;cursor:pointer;font-family:inherit;padding:4px;}\n.lang-btn-sm.active{color:var(--lime);font-weight:600;}\n.main{max-width:1200px;margin:0 auto;padding:24px 20px 60px;}\n.welcome{background:var(--navy);border-radius:var(--radius);padding:22px 26px;margin-bottom:20px;border-left:4px solid var(--lime);}\n.welcome-title{font-size:18px;font-weight:700;color:#fff;letter-spacing:-.02em;}\n.welcome-sub{font-size:13px;color:rgba(255,255,255,.55);margin-top:3px;}\n.kpi-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}\n.kpi{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow);}\n.kpi-val{font-size:26px;font-weight:700;color:var(--navy);font-family:\'DM Mono\',monospace;line-height:1;}\n.kpi-label{font-size:11px;color:var(--text3);margin-top:4px;text-transform:uppercase;letter-spacing:.06em;}\n.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}\n.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;}\n.card-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}\n.card-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text2);}\n.card-body{padding:16px;}\n.empty-state{text-align:center;padding:32px 20px;color:var(--text3);}\n.empty-icon{font-size:32px;margin-bottom:10px;}\n.empty-text{font-size:13px;margin-bottom:14px;}\n.btn-primary{background:var(--navy);color:#fff;border:none;border-radius:7px;padding:9px 18px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s;}\n.btn-primary:hover{background:var(--navy2);}\n.btn-lime{background:var(--lime);color:var(--navy);border:none;border-radius:7px;padding:9px 18px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;}\n.student-row{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:0.5px solid var(--border);}\n.student-row:last-child{border-bottom:none;}\n.student-avatar{width:36px;height:36px;border-radius:50%;background:var(--lime-pale);border:2px solid var(--lime);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:var(--lime-dark);flex-shrink:0;}\n.student-name{font-size:13px;font-weight:500;color:var(--text);}\n.student-sub{font-size:11px;color:var(--text3);}\n.status-dot{width:7px;height:7px;border-radius:50%;margin-left:auto;flex-shrink:0;}\n.status-dot.active{background:var(--green);}\n.status-dot.pending{background:var(--amber);}\n.invite-form{display:flex;gap:8px;margin-top:12px;}\n.invite-input{flex:1;border:1px solid var(--border);border-radius:7px;padding:8px 12px;font-size:13px;font-family:inherit;outline:none;}\n.invite-input:focus{border-color:var(--navy);}\n.quick-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;}\n.qa-btn{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;text-align:center;cursor:pointer;transition:border-color .15s;text-decoration:none;display:block;}\n.qa-btn:hover{border-color:var(--navy);}\n.qa-icon{font-size:22px;margin-bottom:6px;}\n.qa-label{font-size:12px;font-weight:500;color:var(--text);}\n.qa-sub{font-size:10px;color:var(--text3);margin-top:2px;}\n.toast{position:fixed;top:70px;right:20px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;z-index:999;border-left:3px solid var(--lime);display:none;max-width:280px;line-height:1.5;}\n</style>\n</head>\n<body>\n\n<div class="header">\n  <div class="logo">\n    <svg width="28" height="28" viewBox="0 0 64 64" fill="none">\n      <circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/>\n      <circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/>\n      <circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/>\n      <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>\n    </svg>\n    <div>\n      <div class="logo-text">Orbis <span>AI</span></div>\n      <div class="logo-sub" id="h-sub">Coach Dashboard</div>\n    </div>\n  </div>\n  <div class="header-right">\n    <button class="lang-btn-sm active" onclick="setLang(\'en\')" id="lb-en">EN</button>\n    <button class="lang-btn-sm" onclick="setLang(\'es\')" id="lb-es">ES</button>\n    <div class="coach-chip" id="coachName">Coach</div>\n    <button class="btn-logout" onclick="logout()" id="h-logout">Sign out</button>\n  </div>\n</div>\n\n<div class="toast" id="toast"></div>\n\n<div class="main">\n\n  <div class="welcome">\n    <div class="welcome-title" id="w-title">Good morning, Coach 👋</div>\n    <div class="welcome-sub" id="w-sub">Your academy dashboard — manage students, track progress, and let Orbis Core handle the coaching intelligence.</div>\n  </div>\n\n  <div class="kpi-strip">\n    <div class="kpi">\n      <div class="kpi-val" id="k-students">0</div>\n      <div class="kpi-label" id="kl-students">Students</div>\n    </div>\n    <div class="kpi">\n      <div class="kpi-val" id="k-sessions">0</div>\n      <div class="kpi-label" id="kl-sessions">Sessions this month</div>\n    </div>\n    <div class="kpi">\n      <div class="kpi-val" id="k-pending">0</div>\n      <div class="kpi-label" id="kl-pending">Pending invites</div>\n    </div>\n    <div class="kpi">\n      <div class="kpi-val">—</div>\n      <div class="kpi-label" id="kl-bot">Orbis Core bot</div>\n    </div>\n  </div>\n\n  <div class="quick-actions">\n    <a class="qa-btn" href="/dashboard" target="_blank">\n      <div class="qa-icon">🎾</div>\n      <div class="qa-label" id="qa1">View demo</div>\n      <div class="qa-sub" id="qa1s">Fernando\'s full dashboard</div>\n    </a>\n    <a class="qa-btn" href="/report/demo" target="_blank">\n      <div class="qa-icon">📊</div>\n      <div class="qa-label" id="qa2">Progress report</div>\n      <div class="qa-sub" id="qa2s">Demo report — Fernando</div>\n    </a>\n    <a class="qa-btn" href="/evaluation" target="_blank">\n      <div class="qa-icon">📋</div>\n      <div class="qa-label" id="qa3">New evaluation</div>\n      <div class="qa-sub" id="qa3s">Coach + student forms</div>\n    </a>\n  </div>\n\n  <div class="grid2">\n\n    <div class="card">\n      <div class="card-header">\n        <div class="card-title" id="ct-students">My students</div>\n        <button class="btn-primary" onclick="showInvite()" id="ct-invite">+ Invite student</button>\n      </div>\n      <div class="card-body" id="studentsList">\n        <div class="empty-state">\n          <div class="empty-icon">👥</div>\n          <div class="empty-text" id="es-students">No students yet. Invite your first student to get started.</div>\n          <button class="btn-lime" onclick="showInvite()" id="es-btn">Send invitation</button>\n        </div>\n      </div>\n      <div id="inviteForm" style="padding:0 16px 16px;display:none">\n        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--text3);margin-bottom:6px" id="if-label">Invite by email</div>\n        <div class="invite-form">\n          <input class="invite-input" type="email" id="inviteEmail" placeholder="student@email.com">\n          <button class="btn-primary" onclick="sendInvite()" id="if-btn">Send</button>\n        </div>\n      </div>\n    </div>\n\n    <div class="card">\n      <div class="card-header">\n        <div class="card-title" id="ct-orbis">Orbis Core</div>\n        <div style="font-size:11px;color:var(--text3)" id="ct-bot-sub">AI coaching agent</div>\n      </div>\n      <div class="card-body">\n        <div style="background:var(--navy);border-radius:8px;padding:14px 16px;margin-bottom:12px">\n          <div style="font-size:12px;color:rgba(255,255,255,.5);margin-bottom:6px" id="ob-title">Your Orbis Core bot</div>\n          <div style="font-size:13px;color:rgba(255,255,255,.8);line-height:1.5" id="ob-desc">Connect Orbis Core on Telegram to get daily briefings, log sessions by voice, and receive AI coaching recommendations — directly in your chat.</div>\n          <div style="margin-top:10px;background:rgba(62,207,126,.12);border:1px solid rgba(62,207,126,.25);border-radius:6px;padding:8px 12px;font-size:12px;color:var(--lime)" id="ob-coming">🤖 Telegram bot coming soon — Railway deployment in progress</div>\n        </div>\n        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--text3);margin-bottom:8px" id="ob-rag">Knowledge base</div>\n        <div style="display:flex;flex-direction:column;gap:6px">\n          <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2)"><span style="color:var(--green)">✓</span><span id="rag1">ITF Coaching Frameworks (Level 1-3)</span></div>\n          <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2)"><span style="color:var(--green)">✓</span><span id="rag2">Sports science research (HRV, load management)</span></div>\n          <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2)"><span style="color:var(--green)">✓</span><span id="rag3">FIP Padel coaching guidelines</span></div>\n          <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2)"><span style="color:var(--green)">✓</span><span id="rag4">ATP benchmarks (9,500+ matches)</span></div>\n        </div>\n      </div>\n    </div>\n\n  </div>\n</div>\n\n<script>\nconst T = {\n  en: {\n    sub:\'Coach Dashboard\', logout:\'Sign out\',\n    w_title:\'Good morning, Coach\', w_sub:\'Your academy dashboard — manage students, track progress, and let Orbis Core handle the coaching intelligence.\',\n    kl_students:\'Students\', kl_sessions:\'Sessions this month\', kl_pending:\'Pending invites\', kl_bot:\'Orbis Core bot\',\n    qa1:\'View demo\', qa1s:"Fernando\'s full dashboard", qa2:\'Progress report\', qa2s:\'Demo report — Fernando\', qa3:\'New evaluation\', qa3s:\'Coach + student forms\',\n    ct_students:\'My students\', ct_invite:\'+ Invite student\', ct_orbis:\'Orbis Core\', ct_bot_sub:\'AI coaching agent\',\n    es_students:\'No students yet. Invite your first student to get started.\', es_btn:\'Send invitation\',\n    if_label:\'Invite by email\', if_btn:\'Send\',\n    ob_title:\'Your Orbis Core bot\', ob_coming:\'Telegram bot coming soon — Railway deployment in progress\',\n    ob_rag:\'Knowledge base\',\n    rag1:\'ITF Coaching Frameworks (Level 1-3)\', rag2:\'Sports science research (HRV, load management)\',\n    rag3:\'FIP Padel coaching guidelines\', rag4:\'ATP benchmarks (9,500+ matches)\'\n  },\n  es: {\n    sub:\'Panel del Entrenador\', logout:\'Cerrar sesión\',\n    w_title:\'Buenos días, Entrenador\', w_sub:\'Tu panel de academia — gestiona estudiantes, sigue el progreso y deja que Orbis Core se encargue de la inteligencia de entrenamiento.\',\n    kl_students:\'Estudiantes\', kl_sessions:\'Sesiones este mes\', kl_pending:\'Invitaciones pendientes\', kl_bot:\'Bot Orbis Core\',\n    qa1:\'Ver demo\', qa1s:\'Panel completo de Fernando\', qa2:\'Informe de progreso\', qa2s:\'Informe demo — Fernando\', qa3:\'Nueva evaluación\', qa3s:\'Formularios de entrenador y estudiante\',\n    ct_students:\'Mis estudiantes\', ct_invite:\'+ Invitar estudiante\', ct_orbis:\'Orbis Core\', ct_bot_sub:\'Agente de IA de entrenamiento\',\n    es_students:\'Sin estudiantes aún. Invita a tu primer estudiante para empezar.\', es_btn:\'Enviar invitación\',\n    if_label:\'Invitar por correo\', if_btn:\'Enviar\',\n    ob_title:\'Tu bot Orbis Core\', ob_coming:\'Bot de Telegram próximamente — despliegue en Railway en progreso\',\n    ob_rag:\'Base de conocimiento\',\n    rag1:\'Marcos de Coaching ITF (Niveles 1-3)\', rag2:\'Investigación en ciencias del deporte (VFC, gestión de carga)\',\n    rag3:\'Guías de coaching de pádel FIP\', rag4:\'Referencias ATP (más de 9.500 partidos)\'\n  }\n};\n\nlet lang = \'en\';\n\nfunction setLang(l) {\n  lang = l;\n  document.getElementById(\'lb-en\').classList.toggle(\'active\', l===\'en\');\n  document.getElementById(\'lb-es\').classList.toggle(\'active\', l===\'es\');\n  const t = T[l];\n  const ids = [\'sub\',\'w_title\',\'w_sub\',\'kl_students\',\'kl_sessions\',\'kl_pending\',\'kl_bot\',\n    \'qa1\',\'qa1s\',\'qa2\',\'qa2s\',\'qa3\',\'qa3s\',\'ct_students\',\'ct_invite\',\'ct_orbis\',\'ct_bot_sub\',\n    \'es_students\',\'es_btn\',\'if_label\',\'if_btn\',\'ob_title\',\'ob_coming\',\'ob_rag\',\n    \'rag1\',\'rag2\',\'rag3\',\'rag4\'];\n  ids.forEach(k => {\n    const el = document.getElementById(k.includes(\'_\') ? k.replace(/_/g,\'-\').replace(\'h-\',\'h-\') : k);\n    const el2 = document.getElementById(k.replace(/_/g,\'\'));\n    const target = document.getElementById(\'h-sub\') && k===\'sub\' ? document.getElementById(\'h-sub\') :\n                   document.getElementById(\'ct-\'+k.replace(\'ct_\',\'\')) ||\n                   document.getElementById(\'kl-\'+k.replace(\'kl_\',\'\')) ||\n                   document.getElementById(\'qa\'+k.replace(\'qa\',\'\')) ||\n                   document.getElementById(\'es-\'+k.replace(\'es_\',\'\')) ||\n                   document.getElementById(\'if-\'+k.replace(\'if_\',\'\')) ||\n                   document.getElementById(\'ob-\'+k.replace(\'ob_\',\'\')) ||\n                   document.getElementById(\'rag\'+k.replace(\'rag\',\'\')) ||\n                   document.getElementById(\'w-\'+k.replace(\'w_\',\'\')) ||\n                   document.getElementById(k.replace(/_/g,\'-\'));\n    if(target) target.textContent = t[k];\n  });\n  if(document.getElementById(\'h-logout\')) document.getElementById(\'h-logout\').textContent = t.logout;\n  if(document.getElementById(\'w-title\')) document.getElementById(\'w-title\').textContent = t.w_title;\n  if(document.getElementById(\'w-sub\')) document.getElementById(\'w-sub\').textContent = t.w_sub;\n}\n\nfunction logout() {\n  localStorage.removeItem(\'orbis_token\');\n  localStorage.removeItem(\'orbis_role\');\n  localStorage.removeItem(\'orbis_name\');\n  window.location.href = \'/login\';\n}\n\nfunction showInvite() {\n  const f = document.getElementById(\'inviteForm\');\n  f.style.display = f.style.display === \'none\' ? \'block\' : \'none\';\n}\n\nasync function sendInvite() {\n  const email = document.getElementById(\'inviteEmail\').value.trim();\n  if (!email) return;\n  const token = localStorage.getItem(\'orbis_token\');\n\n  try {\n    const res = await fetch(\'/api/invite\', {\n      method: \'POST\',\n      headers: {\'Content-Type\':\'application/json\',\'Authorization\':\'Bearer \'+token},\n      body: JSON.stringify({student_email: email})\n    });\n    if (res.ok) {\n      showToast(lang===\'en\' ? \'✅ Invitation sent to \'+email : \'✅ Invitación enviada a \'+email);\n      document.getElementById(\'inviteEmail\').value = \'\';\n      document.getElementById(\'inviteForm\').style.display = \'none\';\n      document.getElementById(\'k-pending\').textContent =\n        parseInt(document.getElementById(\'k-pending\').textContent||0) + 1;\n    } else {\n      showToast(lang===\'en\' ? \'⚠️ Could not send invitation\' : \'⚠️ No se pudo enviar la invitación\');\n    }\n  } catch(e) {\n    showToast(lang===\'en\' ? \'⚠️ Network error\' : \'⚠️ Error de red\');\n  }\n}\n\nfunction showToast(msg) {\n  const t = document.getElementById(\'toast\');\n  t.textContent = msg;\n  t.style.display = \'block\';\n  setTimeout(() => t.style.display = \'none\', 3000);\n}\n\nasync function loadDashboard() {\n  const name = localStorage.getItem(\'orbis_name\') || \'Coach\';\n  const firstName = name.split(\' \')[0];\n  document.getElementById(\'coachName\').textContent = name;\n  document.getElementById(\'w-title\').textContent =\n    (lang===\'en\' ? \'Good morning, \' : \'Buenos días, \') + firstName + \' 👋\';\n\n  const token = localStorage.getItem(\'orbis_token\');\n  if (!token) { window.location.href = \'/login\'; return; }\n\n  try {\n    const res = await fetch(\'/api/coach/stats\', {\n      headers: {\'Authorization\': \'Bearer \' + token}\n    });\n    if (res.ok) {\n      const data = await res.json();\n      document.getElementById(\'k-students\').textContent = data.students || 0;\n      document.getElementById(\'k-sessions\').textContent = data.sessions || 0;\n      document.getElementById(\'k-pending\').textContent = data.pending_invites || 0;\n    }\n  } catch(e) { console.log(\'Stats not loaded yet\'); }\n}\n\nloadDashboard();\n</script>\n</body>\n</html>'


def load_synthetic_data():
    try:
        with open(DATA_DIR / "player_profile.json") as f: player = json.load(f)
        with open(DATA_DIR / "whoop_recovery.json") as f: whoop = json.load(f)
        with open(DATA_DIR / "match_results.json") as f: matches = json.load(f)
        with open(DATA_DIR / "psychology.json") as f: psych = json.load(f)
        with open(DATA_DIR / "nutrition.json") as f: nutrition = json.load(f)
        return player, whoop, matches, psych, nutrition
    except FileNotFoundError:
        return None, [], [], [], []


class MatchLogEntry(BaseModel):
    player_id: str; date: str; opponent: str; result: str
    score: str; surface: str; duration_minutes: int; physical_feeling: int

class PsychAssessment(BaseModel):
    player_id: str; week_date: str
    q1_performance_worry: float; q2_concentration: float; q3_confidence: float
    q4_irritability: float; q5_sleep_worry: float; q6_motivation: float
    q7_external_coping: float; q8_fatigue_mental: float; q9_enjoyment: float
    q10_pressure: float; coach_notes: str = ""; pre_match_anxiety: float = 5.0
    self_talk_quality: float = 5.0; goal_clarity: float = 5.0

class NutritionLog(BaseModel):
    player_id: str; date: str; total_calories_kcal: int
    protein_g: int; carbohydrates_g: int; fat_g: int
    hydration_liters: float; post_training_meal: str = ""; notes: str = ""


@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbis AI — Tennis & Padel Coaching Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:#f2f0f7;min-height:100vh;display:flex;flex-direction:column;}
.header{background:#3d1a6e;height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 28px;box-shadow:0 2px 12px rgba(61,26,110,.25);}
.logo-name{font-size:16px;font-weight:700;color:#fff;display:flex;align-items:center;gap:10px;}
.logo-name span{color:#3ecf7e;}
.logo-sub{font-size:9px;color:rgba(255,255,255,.4);letter-spacing:.14em;text-transform:uppercase;}
.btn-nav{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);color:rgba(255,255,255,.8);border-radius:6px;padding:7px 16px;font-size:13px;font-weight:500;cursor:pointer;text-decoration:none;}
.btn-nav:hover{background:rgba(255,255,255,.15);}
.btn-nav-lime{background:#3ecf7e;border:none;color:#3d1a6e;border-radius:6px;padding:7px 16px;font-size:13px;font-weight:700;cursor:pointer;text-decoration:none;}
.hero{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 24px;text-align:center;}
.hero-badge{background:rgba(62,207,126,.12);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:5px 14px;font-size:12px;color:#3ecf7e;font-weight:500;margin-bottom:20px;display:inline-block;}
.hero-title{font-size:40px;font-weight:700;color:#1a0a2e;letter-spacing:-.03em;line-height:1.1;margin-bottom:14px;max-width:580px;}
.hero-title span{color:#3d1a6e;}
.hero-sub{font-size:16px;color:#5a4a7a;line-height:1.6;max-width:460px;margin-bottom:36px;}
.hero-btns{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:52px;}
.btn-p{background:#3d1a6e;color:#fff;border:none;border-radius:8px;padding:13px 28px;font-size:15px;font-weight:600;cursor:pointer;text-decoration:none;}
.btn-p:hover{background:#4a2080;}
.btn-s{background:#fff;color:#3d1a6e;border:1.5px solid #e2e6ef;border-radius:8px;padding:13px 28px;font-size:15px;font-weight:600;text-decoration:none;}
.btn-s:hover{border-color:#3d1a6e;}
.btn-d{color:#5a4a7a;font-size:14px;text-decoration:none;padding:13px 8px;}
.btn-d:hover{color:#3d1a6e;text-decoration:underline;}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;max-width:860px;width:100%;}
.feat{background:#fff;border:1px solid #e2e6ef;border-radius:10px;padding:18px 20px;text-align:left;box-shadow:0 1px 4px rgba(61,26,110,.06);}
.feat-icon{font-size:22px;margin-bottom:8px;}
.feat-title{font-size:13px;font-weight:600;color:#1a0a2e;margin-bottom:4px;}
.feat-desc{font-size:12px;color:#5a4a7a;line-height:1.5;}
.footer{padding:20px;text-align:center;font-size:12px;color:#9a8aaa;}
</style>
</head>
<body>
<header class="header">
  <div>
    <div class="logo-name">
      <svg width="26" height="26" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/>
        <circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/>
        <circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/>
        <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>
      </svg>
      Orbis <span>AI</span>
    </div>
    <div class="logo-sub">Data · Insight · Elevate Your Game</div>
  </div>
  <div style="display:flex;gap:10px;align-items:center">
    <a href="/dashboard" class="btn-nav">View demo</a>
    <a href="/login" class="btn-nav">Sign in</a>
    <a href="/register" class="btn-nav-lime">Get started free</a>
  </div>
</header>
<main class="hero">
  <div class="hero-badge">Tennis &amp; Padel Coaching Intelligence</div>
  <h1 class="hero-title">Every data source.<br><span>One coaching intelligence.</span></h1>
  <p class="hero-sub">Orbis AI helps tennis and padel coaches organize their students, track performance, and deliver better results — powered by Orbis Core AI.</p>
  <div class="hero-btns">
    <a href="/register" class="btn-p">Create coach account &rarr;</a>
    <a href="/login" class="btn-s">Sign in</a>
    <a href="/dashboard" class="btn-d">View demo first &rarr;</a>
  </div>
  <div class="features">
    <div class="feat"><div class="feat-icon">📋</div><div class="feat-title">Student management</div><div class="feat-desc">Classes, attendance, payments and progress — all in one place.</div></div>
    <div class="feat"><div class="feat-icon">📊</div><div class="feat-title">Performance evaluations</div><div class="feat-desc">Coach and student dual evaluations generate data-driven progress reports.</div></div>
    <div class="feat"><div class="feat-icon">🤖</div><div class="feat-title">Orbis Core AI</div><div class="feat-desc">Multi-agent AI grounded in ITF frameworks and sports science — via Telegram.</div></div>
    <div class="feat"><div class="feat-icon">🏓</div><div class="feat-title">Tennis &amp; Padel</div><div class="feat-desc">The only platform built for both sports. First mover in padel coaching software.</div></div>
  </div>
</main>
<footer class="footer">Orbis AI &middot; <a href="/docs" style="color:#9a8aaa">API docs</a> &middot; <a href="/dashboard" style="color:#9a8aaa">Demo</a></footer>
</body>
</html>"""

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.2.0",
            "anthropic_connected": bool(os.getenv("ANTHROPIC_API_KEY")),
            "whoop_connected": bool(os.getenv("WHOOP_ACCESS_TOKEN")),
            "synthetic_data_available": DATA_DIR.exists()}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML_CONTENT

@app.get("/auth/whoop/callback")
async def whoop_callback(code: str):
    import httpx
    response = httpx.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={"grant_type": "authorization_code", "code": code,
              "client_id": os.getenv("WHOOP_CLIENT_ID"),
              "client_secret": os.getenv("WHOOP_CLIENT_SECRET"),
              "redirect_uri": "https://ai-tennis-academy-platform-mvp.vercel.app/auth/whoop/callback"})
    if response.status_code == 200:
        t = response.json()
        return {"status": "success", "access_token": t.get("access_token"),
                "refresh_token": t.get("refresh_token"),
                "message": "Copy access_token to Vercel env as WHOOP_ACCESS_TOKEN"}
    return {"status": "error", "detail": response.text}

@app.get("/api/player/{player_id}")
async def get_player(player_id: str):
    player, _, _, _, _ = load_synthetic_data()
    if not player or player.get("player_id") != player_id:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@app.get("/api/player/{player_id}/recovery")
async def get_recovery(player_id: str, days: int = 14):
    _, whoop, _, _, _ = load_synthetic_data()
    wc = WhoopConnector()
    if wc.access_token:
        rd = wc.get_recovery(date.today() - timedelta(days=days), date.today())
        if rd: return {"source": "whoop_api", "data": rd[-days:]}
    return {"source": "synthetic",
            "data": [d for d in whoop if d["player_id"] == player_id][-days:]}

@app.get("/api/player/{player_id}/matches")
async def get_matches(player_id: str, limit: int = 10):
    _, _, matches, _, _ = load_synthetic_data()
    pm = [m for m in matches if m["player_id"] == player_id]
    return {"total": len(pm), "data": pm[-limit:]}

@app.get("/api/player/{player_id}/psychology")
async def get_psychology(player_id: str, weeks: int = 4):
    _, _, _, psych, _ = load_synthetic_data()
    pp = [p for p in psych if p["player_id"] == player_id]
    return {"total_assessments": len(pp), "data": pp[-weeks:]}

@app.get("/api/player/{player_id}/nutrition")
async def get_nutrition(player_id: str, days: int = 7):
    _, _, _, _, nutrition = load_synthetic_data()
    pn = [n for n in nutrition if n["player_id"] == player_id]
    return {"total": len(pn), "data": pn[-days:]}

@app.post("/api/log/match")
async def log_match(entry: MatchLogEntry):
    mf = DATA_DIR / "match_results.json"
    try:
        with open(mf) as f: matches = json.load(f)
    except: matches = []
    nm = entry.dict(); nm["match_id"] = f"M{len(matches)+1:03d}_manual"; nm["source"] = "manual"
    matches.append(nm)
    with open(mf, "w") as f: json.dump(matches, f, indent=2)
    return {"status": "success", "match_id": nm["match_id"]}

@app.get("/api/recommendation/{player_id}")
async def get_recommendation(player_id: str):
    player, whoop_data, matches, psych_data, nutrition_data = load_synthetic_data()
    if not player:
        raise HTTPException(status_code=404, detail="No data found. Run: python scripts/generate_synthetic_data.py")
    pw = [d for d in whoop_data if d["player_id"] == player_id]
    if not pw: raise HTTPException(status_code=404, detail="No recovery data")
    today_data = pw[-1].copy()
    pm = [m for m in matches if m["player_id"] == player_id]
    if pm:
        lm = pm[-1]; today_data.update({"match_played": True,
                                         "match_result": lm["result"], "match_score": lm["score"]})
    wc = WhoopConnector()
    if wc.access_token:
        rt = wc.get_daily_summary(date.today())
        if rt.get("recovery_score"): today_data.update({k:v for k,v in rt.items() if v is not None})
    pp = [p for p in psych_data if p["player_id"] == player_id]
    pn = [n for n in nutrition_data if n["player_id"] == player_id]
    return generate_recommendation(
        player=player, today_data=today_data, history=pw[-14:],
        psychology_data=pp[-1] if pp else None,
        nutrition_data=pn[-2] if len(pn) >= 2 else None,
        upcoming_schedule={"today": "Training session", "tomorrow": "TBD",
                           "next_match": "See tournament calendar"},
        data_dir=str(DATA_DIR))

@app.get("/api/briefing/morning")
async def morning_briefing():
    player, whoop_data, matches, psych_data, nutrition_data = load_synthetic_data()
    if not player: raise HTTPException(status_code=404, detail="No data found")
    return generate_morning_briefing([{
        "player": player, "today": whoop_data[-1] if whoop_data else {},
        "history": whoop_data[-14:],
        "psychology": psych_data[-1] if psych_data else None,
        "nutrition": nutrition_data[-2] if len(nutrition_data) >= 2 else None,
        "upcoming": {"today": "Training", "tomorrow": "TBD", "next_match": "See calendar"},
        "data_dir": str(DATA_DIR)
    }])

@app.get("/evaluation", response_class=HTMLResponse)
async def evaluation_page():
    try:
        f = Path(__file__).parent.parent / "static" / "evaluation.html"
        return f.read_text(encoding="utf-8")
    except Exception as e:
        return f"<h1>Error loading evaluation page: {e}</h1>"

@app.get("/report/demo", response_class=HTMLResponse)
async def report_demo():
    try:
        f = Path(__file__).parent.parent / "static" / "report_demo.html"
        return f.read_text(encoding="utf-8")
    except Exception as e:
        return f"<h1>Error loading report: {e}</h1>"



import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    html = REGISTER_HTML.replace("__SUPABASE_URL__", SUPABASE_URL or "")
    html = html.replace("__SUPABASE_KEY__", os.getenv("SUPABASE_PUBLISHABLE_KEY") or "")
    return html

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return LOGIN_HTML

@app.get("/coach", response_class=HTMLResponse)
async def coach_dashboard():
    return COACH_DASHBOARD_HTML

@app.post("/api/auth/register")
async def api_register(request: Request):
    from fastapi import Request
    body = await request.json()
    sb = get_supabase()
    try:
        # 1 - Create auth user
        auth_res = sb.auth.sign_up({
            "email": body["email"],
            "password": body["password"]
        })
        if not auth_res.user:
            raise HTTPException(status_code=400, detail="Could not create account")
        user_id = auth_res.user.id

        # 2 - Create academy
        sport_map = {
            "tennis": ["tennis"],
            "padel": ["padel"],
            "both": ["tennis", "padel"]
        }
        academy_res = sb.table("academies").insert({
            "name": body["academy_name"],
            "country": body["country"],
            "city": body.get("city", ""),
            "sport": sport_map.get(body.get("sport", "tennis"), ["tennis"])
        }).execute()
        academy_id = academy_res.data[0]["id"]

        # 3 - Create user profile
        sb.table("users").insert({
            "id": user_id,
            "academy_id": academy_id,
            "role": body.get("role", "coach"),
            "full_name": body["full_name"],
            "email": body["email"]
        }).execute()

        return {
            "status": "success",
            "user_id": user_id,
            "academy_id": academy_id,
            "access_token": auth_res.session.access_token if auth_res.session else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/login")
async def api_login(request: Request):
    from fastapi import Request
    body = await request.json()
    sb = get_supabase()
    try:
        auth_res = sb.auth.sign_in_with_password({
            "email": body["email"],
            "password": body["password"]
        })
        if not auth_res.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Get user profile
        user_res = sb.table("users").select("*").eq("id", auth_res.user.id).execute()
        if not user_res.data:
            raise HTTPException(status_code=404, detail="User profile not found")

        user = user_res.data[0]
        return {
            "access_token": auth_res.session.access_token,
            "role": user["role"],
            "full_name": user["full_name"],
            "user_id": user["id"],
            "academy_id": user.get("academy_id")
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/api/invite")
async def send_invite(request: Request):
    from fastapi import Request
    import secrets
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    body = await request.json()
    student_email = body.get("student_email", "").strip()
    if not student_email:
        raise HTTPException(status_code=400, detail="Email required")

    sb = get_supabase()
    try:
        # Verify coach token
        user_res = sb.auth.get_user(token)
        coach_id = user_res.user.id

        # Create invitation
        invite_token = secrets.token_hex(16)
        sb.table("invitations").insert({
            "coach_id": coach_id,
            "student_email": student_email,
            "token": invite_token,
            "status": "pending"
        }).execute()

        # In production: send email with invite link
        # invite_link = f"https://ai-tennis-academy-platform-mvp.vercel.app/activate/{invite_token}"
        # For now: return the link

        return {
            "status": "success",
            "invite_token": invite_token,
            "invite_link": f"/activate/{invite_token}",
            "student_email": student_email
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/coach/stats")
async def coach_stats(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    sb = get_supabase()
    try:
        user_res = sb.auth.get_user(token)
        coach_id = user_res.user.id

        students = sb.table("student_profiles").select("id").eq("coach_id", coach_id).execute()
        pending = sb.table("invitations").select("id").eq("coach_id", coach_id).eq("status", "pending").execute()

        from datetime import date
        first_of_month = date.today().replace(day=1).isoformat()
        sessions = sb.table("sessions").select("id").eq("coach_id", coach_id).gte("session_date", first_of_month).execute()

        return {
            "students": len(students.data),
            "sessions": len(sessions.data),
            "pending_invites": len(pending.data)
        }
    except Exception as e:
        return {"students": 0, "sessions": 0, "pending_invites": 0}


STUDENT_DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbis AI — Student Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--green:#16a34a;--amber:#d97706;--red:#dc2626;--radius:10px;--shadow:0 1px 4px rgba(61,26,110,.08),0 4px 16px rgba(61,26,110,.06);}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);font-size:14px;}
.header{background:var(--navy);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;box-shadow:0 2px 12px rgba(61,26,110,.25);position:sticky;top:0;z-index:100;}
.logo{display:flex;align-items:center;gap:10px;}
.logo-text{font-size:15px;font-weight:700;color:#fff;}.logo-text span{color:var(--lime);}
.logo-sub{font-size:9px;color:rgba(255,255,255,.4);letter-spacing:.14em;text-transform:uppercase;margin-top:1px;}
.header-right{display:flex;align-items:center;gap:10px;}
.student-chip{background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:4px 12px;font-size:12px;color:var(--lime);}
.btn-logout{background:none;border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.6);border-radius:6px;padding:5px 12px;font-size:11px;cursor:pointer;font-family:inherit;}
.lang-btn-sm{background:none;border:none;color:rgba(255,255,255,.4);font-size:11px;cursor:pointer;font-family:inherit;padding:4px;}
.lang-btn-sm.active{color:var(--lime);font-weight:600;}
.main{max-width:1200px;margin:0 auto;padding:24px 20px 60px;}
.welcome{background:var(--navy);border-radius:var(--radius);padding:22px 26px;margin-bottom:20px;border-left:4px solid var(--lime);}
.welcome-title{font-size:18px;font-weight:700;color:#fff;letter-spacing:-.02em;}
.welcome-sub{font-size:13px;color:rgba(255,255,255,.55);margin-top:3px;}
.kpi-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow);}
.kpi-val{font-size:26px;font-weight:700;color:var(--navy);font-family:'DM Mono',monospace;line-height:1;}
.kpi-val.lime{color:var(--lime-dark);}
.kpi-label{font-size:11px;color:var(--text3);margin-top:4px;text-transform:uppercase;letter-spacing:.06em;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;}
.card-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.card-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text2);}
.card-body{padding:16px;}
.quick-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;}
.qa-btn{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;text-align:center;cursor:pointer;transition:border-color .15s;text-decoration:none;display:block;}
.qa-btn:hover{border-color:var(--navy);}
.qa-icon{font-size:22px;margin-bottom:6px;}
.qa-label{font-size:12px;font-weight:500;color:var(--text);}
.qa-sub{font-size:10px;color:var(--text3);margin-top:2px;}
.skill-row{margin-bottom:14px;}
.skill-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;}
.skill-name{font-size:12px;font-weight:500;color:var(--text);}
.skill-scores{display:flex;gap:8px;font-size:11px;}
.score-coach{color:var(--navy);font-weight:600;}
.score-self{color:var(--lime-dark);font-weight:600;}
.skill-bar-bg{height:6px;background:var(--bg);border-radius:3px;position:relative;overflow:hidden;}
.skill-bar-coach{height:100%;background:var(--navy);border-radius:3px;transition:width .6s ease;}
.skill-bar-self{height:3px;background:var(--lime);border-radius:3px;position:absolute;top:0;transition:width .6s ease;}
.session-row{display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:0.5px solid var(--border);}
.session-row:last-child{border-bottom:none;}
.session-dot{width:8px;height:8px;border-radius:50%;background:var(--lime);margin-top:4px;flex-shrink:0;}
.session-date{font-size:11px;color:var(--text3);min-width:70px;}
.session-text{font-size:12px;color:var(--text2);line-height:1.5;}
.coach-card{display:flex;align-items:center;gap:14px;background:var(--bg);border-radius:8px;padding:14px;}
.coach-avatar{width:44px;height:44px;border-radius:50%;background:var(--navy);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;color:var(--lime);flex-shrink:0;}
.coach-name{font-size:13px;font-weight:600;color:var(--text);}
.coach-sub{font-size:11px;color:var(--text3);margin-top:2px;}
.next-session{background:linear-gradient(135deg,var(--navy),var(--navy2));border-radius:8px;padding:14px 16px;color:#fff;}
.next-label{font-size:10px;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px;}
.next-date{font-size:15px;font-weight:700;color:#fff;}
.next-focus{font-size:12px;color:rgba(255,255,255,.6);margin-top:4px;}
.empty-state{text-align:center;padding:28px 20px;color:var(--text3);}
.empty-icon{font-size:28px;margin-bottom:8px;}
.empty-text{font-size:12px;}
.toast{position:fixed;top:70px;right:20px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;z-index:999;border-left:3px solid var(--lime);display:none;max-width:280px;line-height:1.5;}
.badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:600;}
.badge-green{background:var(--lime-pale);color:var(--lime-dark);}
.connect-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
.connect-btn{display:flex;align-items:center;gap:10px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;cursor:pointer;transition:border-color .15s;width:100%;font-family:inherit;}
.connect-btn:hover{border-color:var(--navy);}
.connect-btn.connected{border-color:var(--lime);background:var(--lime-pale);}
.connect-icon{font-size:18px;}
.connect-name{font-size:12px;font-weight:500;color:var(--text);text-align:left;}
.connect-status{font-size:10px;margin-top:1px;text-align:left;}
.connect-status.on{color:var(--lime-dark);}
.connect-status.off{color:var(--text3);}
.upload-zone{border:1.5px dashed var(--border);border-radius:8px;padding:20px;text-align:center;cursor:pointer;transition:border-color .15s;margin-bottom:10px;}
.upload-zone:hover{border-color:var(--navy);}
.upload-icon{font-size:24px;margin-bottom:6px;}
.upload-label{font-size:12px;color:var(--text2);font-weight:500;}
.upload-sub{font-size:10px;color:var(--text3);margin-top:2px;}
.upload-list{display:flex;flex-direction:column;gap:6px;}
.upload-item{display:flex;align-items:center;gap:8px;background:var(--bg);border-radius:6px;padding:8px 10px;font-size:11px;color:var(--text2);}
.upload-item-icon{font-size:14px;}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <svg width="28" height="28" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>
    </svg>
    <div>
      <div class="logo-text">Orbis <span>AI</span></div>
      <div class="logo-sub" id="h-sub">Student Dashboard</div>
    </div>
  </div>
  <div class="header-right">
    <button class="lang-btn-sm active" onclick="setLang('en')" id="lb-en">EN</button>
    <button class="lang-btn-sm" onclick="setLang('es')" id="lb-es">ES</button>
    <div class="student-chip" id="studentName">Student</div>
    <button class="btn-logout" onclick="logout()" id="h-logout">Sign out</button>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="main">

  <div class="welcome">
    <div class="welcome-title" id="w-title">Good morning &#x1F44B;</div>
    <div class="welcome-sub" id="w-sub">Your personal performance hub — track your progress, connect your devices, and stay in sync with your coach.</div>
  </div>

  <div class="kpi-strip">
    <div class="kpi"><div class="kpi-val lime" id="k-level">&#8212;</div><div class="kpi-label" id="kl-level">Current level</div></div>
    <div class="kpi"><div class="kpi-val" id="k-sessions">0</div><div class="kpi-label" id="kl-sessions">Sessions logged</div></div>
    <div class="kpi"><div class="kpi-val" id="k-evals">0</div><div class="kpi-label" id="kl-evals">Evaluations</div></div>
    <div class="kpi"><div class="kpi-val" id="k-streak">0</div><div class="kpi-label" id="kl-streak">Week streak</div></div>
  </div>

  <div class="quick-actions">
    <a class="qa-btn" href="/report/demo" target="_blank">
      <div class="qa-icon">&#x1F4CA;</div>
      <div class="qa-label" id="qa1">My progress report</div>
      <div class="qa-sub" id="qa1s">Latest evaluation results</div>
    </a>
    <a class="qa-btn" href="/evaluation" target="_blank">
      <div class="qa-icon">&#x1F4CB;</div>
      <div class="qa-label" id="qa2">Self evaluation</div>
      <div class="qa-sub" id="qa2s">Rate your last session</div>
    </a>
    <a class="qa-btn" href="#" onclick="window.open('https://t.me/orbiscoreai_bot', '_blank'); return false;">
      <div class="qa-icon">&#x1F916;</div>
      <div class="qa-label" id="qa3">Ask Orbis Core</div>
      <div class="qa-sub" id="qa3s">AI coaching assistant</div>
    </a>
  </div>

  <div class="grid2">

    <div class="card">
      <div class="card-header">
        <div class="card-title" id="ct-skills">My skills</div>
        <span class="badge badge-green" id="skills-badge">Latest eval</span>
      </div>
      <div class="card-body" id="skillsBody">
        <div class="empty-state">
          <div class="empty-icon">&#x1F3BE;</div>
          <div class="empty-text" id="es-skills">No evaluations yet. Your coach will run your first one soon.</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title" id="ct-coach">My coach</div>
      </div>
      <div class="card-body">
        <div class="coach-card">
          <div class="coach-avatar" id="coachInitials">&#8212;</div>
          <div>
            <div class="coach-name" id="coachFullName">Loading...</div>
            <div class="coach-sub" id="coachAcademy">Academy</div>
          </div>
        </div>
        <div style="margin-top:14px">
          <div class="next-session">
            <div class="next-label" id="ns-label">Next session</div>
            <div class="next-date" id="ns-date">&#8212;</div>
            <div class="next-focus" id="ns-focus">No upcoming session scheduled</div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <div class="grid2">

    <div class="card">
      <div class="card-header">
        <div class="card-title" id="ct-wearables">My devices</div>
        <span style="font-size:11px;color:var(--text3)" id="wearables-sub">Connect to share data</span>
      </div>
      <div class="card-body">
        <div class="connect-grid">
          <button class="connect-btn" id="btn-whoop" onclick="connectDevice('whoop')">
            <span class="connect-icon">&#x231A;</span>
            <div><div class="connect-name">Whoop</div><div class="connect-status off" id="status-whoop">Not connected</div></div>
          </button>
          <button class="connect-btn" id="btn-apple" onclick="connectDevice('apple')">
            <span class="connect-icon">&#x1F34E;</span>
            <div><div class="connect-name">Apple Health</div><div class="connect-status off" id="status-apple">Not connected</div></div>
          </button>
          <button class="connect-btn" id="btn-garmin" onclick="connectDevice('garmin')">
            <span class="connect-icon">&#x1F9ED;</span>
            <div><div class="connect-name">Garmin</div><div class="connect-status off" id="status-garmin">Not connected</div></div>
          </button>
          <button class="connect-btn" id="btn-fitbit" onclick="connectDevice('fitbit')">
            <span class="connect-icon">&#x1F49A;</span>
            <div><div class="connect-name">Fitbit</div><div class="connect-status off" id="status-fitbit">Not connected</div></div>
          </button>
        </div>
        <div style="margin-top:10px;font-size:10px;color:var(--text3);text-align:center" id="wearables-note">V1: PDF export supported. API connections coming soon.</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title" id="ct-docs">My documents</div>
        <span style="font-size:11px;color:var(--text3)">PDF · Excel · Word</span>
      </div>
      <div class="card-body">
        <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
          <div class="upload-icon">&#x1F4C1;</div>
          <div class="upload-label" id="upload-label">Upload a document</div>
          <div class="upload-sub" id="upload-sub">Health report, training plan, nutrition guide</div>
        </div>
        <input type="file" id="fileInput" style="display:none" accept=".pdf,.xlsx,.xls,.csv,.docx,.doc" onchange="handleUpload(this)">
        <div class="upload-list" id="uploadList"></div>
      </div>
    </div>

  </div>

  <div class="card">
    <div class="card-header">
      <div class="card-title" id="ct-history">Session history</div>
      <span style="font-size:11px;color:var(--text3)" id="history-sub">Last 5 sessions</span>
    </div>
    <div class="card-body" id="sessionHistory">
      <div class="empty-state">
        <div class="empty-icon">&#x1F4C5;</div>
        <div class="empty-text" id="es-history">No sessions logged yet.</div>
      </div>
    </div>
  </div>

</div>

<script>
const T = {
  en:{
    sub:'Student Dashboard',logout:'Sign out',
    w_sub:'Your personal performance hub — track your progress, connect your devices, and stay in sync with your coach.',
    kl_level:'Current level',kl_sessions:'Sessions logged',kl_evals:'Evaluations',kl_streak:'Week streak',
    qa1:'My progress report',qa1s:'Latest evaluation results',qa2:'Self evaluation',qa2s:'Rate your last session',qa3:'Ask Orbis Core',qa3s:'AI coaching assistant',
    ct_skills:'My skills',ct_coach:'My coach',ct_wearables:'My devices',ct_docs:'My documents',ct_history:'Session history',
    es_skills:'No evaluations yet. Your coach will run your first one soon.',
    es_history:'No sessions logged yet.',
    ns_label:'Next session',
    upload_label:'Upload a document',upload_sub:'Health report, training plan, nutrition guide',
    wearables_note:'V1: PDF export supported. API connections coming soon.'
  },
  es:{
    sub:'Panel del Estudiante',logout:'Cerrar sesión',
    w_sub:'Tu hub de rendimiento personal — sigue tu progreso, conecta tus dispositivos y mantente sincronizado con tu entrenador.',
    kl_level:'Nivel actual',kl_sessions:'Sesiones registradas',kl_evals:'Evaluaciones',kl_streak:'Racha semanal',
    qa1:'Mi informe de progreso',qa1s:'Últimos resultados',qa2:'Autoevaluación',qa2s:'Valora tu última sesión',qa3:'Preguntar a Orbis Core',qa3s:'Asistente de IA',
    ct_skills:'Mis habilidades',ct_coach:'Mi entrenador',ct_wearables:'Mis dispositivos',ct_docs:'Mis documentos',ct_history:'Historial de sesiones',
    es_skills:'Sin evaluaciones aún. Tu entrenador hará la primera pronto.',
    es_history:'Sin sesiones registradas aún.',
    ns_label:'Próxima sesión',
    upload_label:'Subir un documento',upload_sub:'Informe de salud, plan de entrenamiento, guía nutricional',
    wearables_note:'V1: exportación PDF compatible. Conexiones API próximamente.'
  }
};

let lang='en';
function setLang(l){
  lang=l;
  document.getElementById('lb-en').classList.toggle('active',l==='en');
  document.getElementById('lb-es').classList.toggle('active',l==='es');
  const t=T[l];
  document.getElementById('h-sub').textContent=t.sub;
  document.getElementById('h-logout').textContent=t.logout;
  document.getElementById('w-sub').textContent=t.w_sub;
  document.getElementById('kl-level').textContent=t.kl_level;
  document.getElementById('kl-sessions').textContent=t.kl_sessions;
  document.getElementById('kl-evals').textContent=t.kl_evals;
  document.getElementById('kl-streak').textContent=t.kl_streak;
  document.getElementById('qa1').textContent=t.qa1;
  document.getElementById('qa1s').textContent=t.qa1s;
  document.getElementById('qa2').textContent=t.qa2;
  document.getElementById('qa2s').textContent=t.qa2s;
  document.getElementById('qa3').textContent=t.qa3;
  document.getElementById('qa3s').textContent=t.qa3s;
  document.getElementById('ct-skills').textContent=t.ct_skills;
  document.getElementById('ct-coach').textContent=t.ct_coach;
  document.getElementById('ct-wearables').textContent=t.ct_wearables;
  document.getElementById('ct-docs').textContent=t.ct_docs;
  document.getElementById('ct-history').textContent=t.ct_history;
  document.getElementById('ns-label').textContent=t.ns_label;
  document.getElementById('upload-label').textContent=t.upload_label;
  document.getElementById('upload-sub').textContent=t.upload_sub;
  document.getElementById('wearables-note').textContent=t.wearables_note;
  const name=localStorage.getItem('orbis_name')||'';
  document.getElementById('w-title').textContent=(l==='en'?'Good morning, ':'Buenos días, ')+name.split(' ')[0]+' 👋';
}

function logout(){
  localStorage.removeItem('orbis_token');
  localStorage.removeItem('orbis_role');
  localStorage.removeItem('orbis_name');
  window.location.href='/login';
}

function showToast(msg){
  const t=document.getElementById('toast');
  t.textContent=msg;
  t.style.display='block';
  setTimeout(()=>t.style.display='none',3000);
}

function connectDevice(device){
  showToast('API connection coming soon — upload a PDF export for now');
}

function handleUpload(input){
  const file=input.files[0];
  if(!file)return;
  const icons={pdf:'📄',xlsx:'📊',xls:'📊',csv:'📊',docx:'📝',doc:'📝'};
  const ext=file.name.split('.').pop().toLowerCase();
  const icon=icons[ext]||'📎';
  const list=document.getElementById('uploadList');
  const item=document.createElement('div');
  item.className='upload-item';
  item.innerHTML=`<span class="upload-item-icon">${icon}</span><span>${file.name}</span><span style="margin-left:auto;color:var(--amber);font-size:10px">Uploading...</span>`;
  list.appendChild(item);
  showToast('Document received — backend upload coming soon');
}

function renderSkills(skills){
  if(!skills||!skills.length)return;
  document.getElementById('skillsBody').innerHTML=skills.map(s=>`
    <div class="skill-row">
      <div class="skill-header">
        <div class="skill-name">${s.name}</div>
        <div class="skill-scores"><span class="score-coach">Coach: ${s.coach_score}/5</span><span class="score-self">Self: ${s.self_score}/5</span></div>
      </div>
      <div class="skill-bar-bg">
        <div class="skill-bar-coach" style="width:${(s.coach_score/5)*100}%"></div>
        <div class="skill-bar-self" style="width:${(s.self_score/5)*100}%"></div>
      </div>
    </div>`).join('');
}

function renderSessions(sessions){
  if(!sessions||!sessions.length)return;
  document.getElementById('sessionHistory').innerHTML=sessions.map(s=>`
    <div class="session-row">
      <div class="session-dot"></div>
      <div class="session-date">${s.date}</div>
      <div class="session-text">${s.notes||'Session logged'}</div>
    </div>`).join('');
}

async function loadDashboard(){
  const name=localStorage.getItem('orbis_name')||'Student';
  document.getElementById('studentName').textContent=name;
  document.getElementById('w-title').textContent='Good morning, '+name.split(' ')[0]+' 👋';
  const token=localStorage.getItem('orbis_token');
  if(!token){window.location.href='/login';return;}
  try{
    const res=await fetch('/api/student/dashboard',{headers:{'Authorization':'Bearer '+token}});
    if(res.ok){
      const data=await res.json();
      document.getElementById('k-level').textContent=data.level||'\u2014';
      document.getElementById('k-sessions').textContent=data.sessions_count||0;
      document.getElementById('k-evals').textContent=data.evals_count||0;
      document.getElementById('k-streak').textContent=data.streak||0;
      if(data.coach_name){
        const initials=data.coach_name.split(' ').map(w=>w[0]).join('').toUpperCase();
        document.getElementById('coachInitials').textContent=initials;
        document.getElementById('coachFullName').textContent=data.coach_name;
        document.getElementById('coachAcademy').textContent=data.academy_name||'Academy';
      }
      if(data.next_session){
        document.getElementById('ns-date').textContent=data.next_session.date;
        document.getElementById('ns-focus').textContent=data.next_session.focus||'';
      }
      if(data.latest_skills)renderSkills(data.latest_skills);
      if(data.sessions)renderSessions(data.sessions);
    }
  }catch(e){console.log('Dashboard not loaded');}
}

loadDashboard();
</script>
</body>
</html>'''

@app.get("/student/dashboard", response_class=HTMLResponse)
async def student_dashboard():
    return STUDENT_DASHBOARD_HTML

@app.get("/api/student/dashboard")
async def student_dashboard_api(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    sb = get_supabase()
    try:
        user_res = sb.auth.get_user(token)
        student_id = user_res.user.id
        profile = sb.table("student_profiles").select("*").eq("user_id", student_id).execute()
        evals = sb.table("evaluations").select("*").eq("student_id", student_id).order("created_at", desc=True).limit(5).execute()
        sessions = sb.table("sessions").select("*").eq("student_id", student_id).order("session_date", desc=True).limit(5).execute()
        coach_data = {}
        if profile.data and profile.data[0].get("coach_id"):
            coach = sb.table("users").select("full_name,academy_id").eq("id", profile.data[0]["coach_id"]).execute()
            if coach.data:
                coach_data = coach.data[0]
                if coach_data.get("academy_id"):
                    acad = sb.table("academies").select("name").eq("id", coach_data["academy_id"]).execute()
                    coach_data["academy_name"] = acad.data[0]["name"] if acad.data else ""
        latest_skills = []
        if evals.data:
            ev = evals.data[0]
            latest_skills = [
                {"name": "Forehand", "coach_score": ev.get("forehand_coach", 0), "self_score": ev.get("forehand_self", 0)},
                {"name": "Backhand", "coach_score": ev.get("backhand_coach", 0), "self_score": ev.get("backhand_self", 0)},
                {"name": "Serve", "coach_score": ev.get("serve_coach", 0), "self_score": ev.get("serve_self", 0)},
                {"name": "Movement", "coach_score": ev.get("movement_coach", 0), "self_score": ev.get("movement_self", 0)},
                {"name": "Tactical", "coach_score": ev.get("tactical_coach", 0), "self_score": ev.get("tactical_self", 0)},
            ]
        return {
            "level": profile.data[0].get("level", "—") if profile.data else "—",
            "sessions_count": len(sessions.data),
            "evals_count": len(evals.data),
            "streak": 0,
            "coach_name": coach_data.get("full_name", ""),
            "academy_name": coach_data.get("academy_name", ""),
            "latest_skills": latest_skills,
            "sessions": [{"date": s["session_date"], "notes": s.get("notes", "")} for s in sessions.data]
        }
    except Exception as e:
        return {"level": "—", "sessions_count": 0, "evals_count": 0, "streak": 0, "coach_name": "", "academy_name": "", "latest_skills": [], "sessions": []}


DEMO_COACH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbis AI — Coach Demo</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--green:#16a34a;--amber:#d97706;--red:#dc2626;--radius:10px;--shadow:0 1px 4px rgba(61,26,110,.08),0 4px 16px rgba(61,26,110,.06);}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);font-size:14px;}
.header{background:var(--navy);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;box-shadow:0 2px 12px rgba(61,26,110,.25);position:sticky;top:0;z-index:100;}
.logo{display:flex;align-items:center;gap:10px;}
.logo-text{font-size:15px;font-weight:700;color:#fff;}.logo-text span{color:var(--lime);}
.logo-sub{font-size:9px;color:rgba(255,255,255,.4);letter-spacing:.14em;text-transform:uppercase;margin-top:1px;}
.demo-badge{background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:4px 12px;font-size:11px;color:var(--lime);font-weight:600;}
.btn-back{background:none;border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.6);border-radius:6px;padding:5px 12px;font-size:11px;cursor:pointer;font-family:inherit;text-decoration:none;}
.main{max-width:1200px;margin:0 auto;padding:24px 20px 60px;}
.welcome{background:var(--navy);border-radius:var(--radius);padding:22px 26px;margin-bottom:20px;border-left:4px solid var(--lime);}
.welcome-title{font-size:18px;font-weight:700;color:#fff;letter-spacing:-.02em;}
.welcome-sub{font-size:13px;color:rgba(255,255,255,.55);margin-top:3px;}
.kpi-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow);}
.kpi-val{font-size:26px;font-weight:700;color:var(--navy);font-family:'DM Mono',monospace;line-height:1;}
.kpi-val.lime{color:var(--lime-dark);}
.kpi-label{font-size:11px;color:var(--text3);margin-top:4px;text-transform:uppercase;letter-spacing:.06em;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;}
.card-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.card-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text2);}
.card-body{padding:16px;}
.student-row{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:0.5px solid var(--border);cursor:pointer;transition:background .1s;}
.student-row:last-child{border-bottom:none;}
.student-row:hover{background:var(--bg);margin:0 -16px;padding:11px 16px;}
.student-avatar{width:38px;height:38px;border-radius:50%;background:var(--lime-pale);border:2px solid var(--lime);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:var(--lime-dark);flex-shrink:0;}
.student-avatar.pending{background:#f2f0f7;border-color:var(--border);color:var(--text3);}
.student-info{flex:1;}
.student-name{font-size:13px;font-weight:500;color:var(--text);}
.student-sub{font-size:11px;color:var(--text3);margin-top:1px;}
.student-stats{display:flex;gap:12px;align-items:center;}
.stat-pill{font-size:11px;font-family:'DM Mono',monospace;font-weight:600;}
.stat-pill.green{color:var(--green);}
.stat-pill.amber{color:var(--amber);}
.stat-pill.muted{color:var(--text3);}
.status-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.status-dot.active{background:var(--green);}
.status-dot.pending{background:var(--amber);}
.skill-row{margin-bottom:12px;}
.skill-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}
.skill-name{font-size:12px;font-weight:500;color:var(--text);}
.skill-scores{display:flex;gap:8px;font-size:11px;}
.score-coach{color:var(--navy);font-weight:600;}
.score-self{color:var(--lime-dark);font-weight:600;}
.skill-bar-bg{height:6px;background:var(--bg);border-radius:3px;position:relative;overflow:hidden;}
.skill-bar-coach{height:100%;background:var(--navy);border-radius:3px;}
.skill-bar-self{height:3px;background:var(--lime);border-radius:3px;position:absolute;top:0;}
.rec-strip{background:var(--navy);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow);border-left:4px solid var(--lime);margin-top:16px;}
.rec-header{padding:12px 16px;border-bottom:1px solid rgba(255,255,255,.08);display:flex;align-items:center;justify-content:space-between;}
.rec-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:rgba(255,255,255,.7);}
.rec-grid{display:grid;grid-template-columns:1fr 1fr;gap:0;}
.rec-block{padding:14px 16px;border-right:1px solid rgba(255,255,255,.07);}
.rec-block:nth-child(2){border-right:none;}
.rec-block:nth-child(3){border-right:1px solid rgba(255,255,255,.07);border-top:1px solid rgba(255,255,255,.07);}
.rec-block:nth-child(4){border-top:1px solid rgba(255,255,255,.07);}
.rec-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--lime);margin-bottom:6px;}
.rec-text{font-size:12px;color:rgba(255,255,255,.8);line-height:1.6;}
.orbis-panel{background:var(--navy);border-radius:8px;padding:14px 16px;margin-bottom:12px;}
.quick-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;}
.qa-btn{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;text-align:center;cursor:pointer;transition:border-color .15s;text-decoration:none;display:block;}
.qa-btn:hover{border-color:var(--navy);}
.qa-icon{font-size:22px;margin-bottom:6px;}
.qa-label{font-size:12px;font-weight:500;color:var(--text);}
.qa-sub{font-size:10px;color:var(--text3);margin-top:2px;}
.chart-wrap{position:relative;height:100px;}
.toast{position:fixed;top:70px;right:20px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;z-index:999;border-left:3px solid var(--lime);display:none;max-width:280px;line-height:1.5;}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <svg width="28" height="28" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>
    </svg>
    <div>
      <div class="logo-text">Orbis <span>AI</span></div>
      <div class="logo-sub">Coach Dashboard</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:10px;">
    <span class="demo-badge">Demo mode</span>
    <a href="/" class="btn-back">Back to home</a>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="main">

  <div class="welcome">
    <div class="welcome-title">Good morning, Coach Toni 👋</div>
    <div class="welcome-sub">Roger Lederer Academy — 3 students enrolled · Orbis Core active · Demo data</div>
  </div>

  <div class="kpi-strip">
    <div class="kpi"><div class="kpi-val">3</div><div class="kpi-label">Students</div></div>
    <div class="kpi"><div class="kpi-val">14</div><div class="kpi-label">Sessions this month</div></div>
    <div class="kpi"><div class="kpi-val lime">84%</div><div class="kpi-label">Avg recovery</div></div>
    <div class="kpi"><div class="kpi-val">2</div><div class="kpi-label">Pending evals</div></div>
  </div>

  <div class="quick-actions">
    <a class="qa-btn" href="/demo/student">
      <div class="qa-icon">&#x1F468;</div>
      <div class="qa-label">Student view</div>
      <div class="qa-sub">Fernando's dashboard</div>
    </a>
    <a class="qa-btn" href="/report/demo">
      <div class="qa-icon">&#x1F4CA;</div>
      <div class="qa-label">Progress report</div>
      <div class="qa-sub">Fernando's latest eval</div>
    </a>
    <a class="qa-btn" href="#" onclick="window.open('https://t.me/orbiscoreai_bot', '_blank'); return false;">
      <div class="qa-icon">&#x1F916;</div>
      <div class="qa-label">Ask Orbis Core</div>
      <div class="qa-sub">AI coaching agent</div>
    </a>
  </div>

  <div class="grid2">

    <!-- Student roster -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">My students</div>
        <span style="font-size:11px;color:var(--text3)">3 enrolled</span>
      </div>
      <div class="card-body">

        <!-- Fernando — active -->
        <div class="student-row" onclick="window.location.href='/demo/student'">
          <div class="student-avatar">F</div>
          <div class="student-info">
            <div class="student-name">Fernando de los Rios</div>
            <div class="student-sub">Advanced recreational · Clay specialist</div>
          </div>
          <div class="student-stats">
            <span class="stat-pill green">84% rec</span>
            <span class="stat-pill">57ms HRV</span>
            <div class="status-dot active"></div>
          </div>
        </div>

        <!-- James — pending eval -->
        <div class="student-row">
          <div class="student-avatar pending">J</div>
          <div class="student-info">
            <div class="student-name">James Hartwell</div>
            <div class="student-sub">Intermediate · Evaluation pending</div>
          </div>
          <div class="student-stats">
            <span class="stat-pill muted">No wearable</span>
            <div class="status-dot pending"></div>
          </div>
        </div>

        <!-- Jaime — pending eval -->
        <div class="student-row">
          <div class="student-avatar pending">J</div>
          <div class="student-info">
            <div class="student-name">Jaime Robles</div>
            <div class="student-sub">Competitive junior · Padel focus</div>
          </div>
          <div class="student-stats">
            <span class="stat-pill muted">No wearable</span>
            <div class="status-dot pending"></div>
          </div>
        </div>

      </div>
    </div>

    <!-- Fernando skills + recovery -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">Fernando — latest evaluation</div>
        <span style="font-size:11px;color:var(--text3)">Jun 15, 2026</span>
      </div>
      <div class="card-body">
        <div style="display:flex;gap:8px;margin-bottom:12px;font-size:11px;">
          <span style="display:flex;align-items:center;gap:4px;color:var(--text3)"><span style="width:8px;height:8px;background:var(--navy);border-radius:50%;display:inline-block;"></span>Coach</span>
          <span style="display:flex;align-items:center;gap:4px;color:var(--text3)"><span style="width:8px;height:8px;background:var(--lime);border-radius:50%;display:inline-block;"></span>Self</span>
        </div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Forehand</div><div class="skill-scores"><span class="score-coach">4.2/5</span><span class="score-self">4.0/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:84%"></div><div class="skill-bar-self" style="width:80%"></div></div></div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Backhand</div><div class="skill-scores"><span class="score-coach">3.5/5</span><span class="score-self">3.2/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:70%"></div><div class="skill-bar-self" style="width:64%"></div></div></div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Serve</div><div class="skill-scores"><span class="score-coach">3.8/5</span><span class="score-self">4.0/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:76%"></div><div class="skill-bar-self" style="width:80%"></div></div></div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Movement</div><div class="skill-scores"><span class="score-coach">4.0/5</span><span class="score-self">3.8/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:80%"></div><div class="skill-bar-self" style="width:76%"></div></div></div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Tactical</div><div class="skill-scores"><span class="score-coach">3.2/5</span><span class="score-self">3.0/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:64%"></div><div class="skill-bar-self" style="width:60%"></div></div></div>

        <!-- Recovery chart -->
        <div style="margin-top:14px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text3);margin-bottom:6px;">14-day recovery trend</div>
        <div class="chart-wrap"><canvas id="recoveryChart"></canvas></div>
      </div>
    </div>

  </div>

  <!-- Orbis Core AI recommendation -->
  <div class="rec-strip">
    <div class="rec-header">
      <div class="rec-title">Orbis Core — AI coaching recommendation · Fernando</div>
      <span style="font-size:10px;color:rgba(255,255,255,.3);">claude-sonnet-4-6 · ITF + FIP + ATP data</span>
    </div>
    <div class="rec-grid">
      <div class="rec-block">
        <div class="rec-label">Key finding</div>
        <div class="rec-text">Fernando's backhand under pressure is the primary technical gap. Coach scores (3.5) align with match data showing 22 unforced errors/match concentrated on backhand cross-court exchanges.</div>
      </div>
      <div class="rec-block">
        <div class="rec-label">Today's recommendation</div>
        <div class="rec-text">Recovery at 84% — green light for high-intensity session. Focus on backhand slice as a defensive reset pattern (ITF Level 2 framework), reducing error count by creating neutral ball opportunities.</div>
      </div>
      <div class="rec-block">
        <div class="rec-label">Cross-data insight</div>
        <div class="rec-text">HRV at 57ms (7d avg 54ms) trending upward — Fernando's best tactical performances correlate with HRV above 55ms. Schedule match-play scenarios on high-HRV days for maximum transfer.</div>
      </div>
      <div class="rec-block">
        <div class="rec-label">Watch this week</div>
        <div class="rec-text">Pre-match anxiety score is 3.8/10 — within acceptable range but higher than baseline. Monitor self-talk quality metric after Tuesday's match and adjust warm-up routine if anxiety exceeds 5.0.</div>
      </div>
    </div>
    <div style="padding:10px 16px;border-top:1px solid rgba(255,255,255,.07);display:flex;gap:8px;flex-wrap:wrap;">
      <span style="font-size:10px;padding:3px 9px;border-radius:20px;background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.25);color:var(--lime);font-family:'DM Mono',monospace;">WHOOP</span>
      <span style="font-size:10px;padding:3px 9px;border-radius:20px;background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.25);color:var(--lime);font-family:'DM Mono',monospace;">ITF frameworks</span>
      <span style="font-size:10px;padding:3px 9px;border-radius:20px;background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.25);color:var(--lime);font-family:'DM Mono',monospace;">ATP benchmarks</span>
      <span style="font-size:10px;padding:3px 9px;border-radius:20px;background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.25);color:var(--lime);font-family:'DM Mono',monospace;">APSQ psychology</span>
    </div>
  </div>

</div>

<script>
function showToast(msg){const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';setTimeout(()=>t.style.display='none',3000);}

const recovData = [72,68,75,80,84,78,82,85,79,83,88,84,80,84];
const recovLabels = ['Jun 8','Jun 9','Jun 10','Jun 11','Jun 12','Jun 13','Jun 14','Jun 15','Jun 16','Jun 17','Jun 18','Jun 19','Jun 20','Jun 21'];
function rcol(v){return v>=75?'#16a34a':v>=55?'#d97706':'#dc2626';}
new Chart(document.getElementById('recoveryChart'),{
  type:'bar',
  data:{labels:recovLabels,datasets:[{data:recovData,backgroundColor:recovData.map(v=>rcol(v)+'33'),borderColor:recovData.map(v=>rcol(v)),borderWidth:1.5,borderRadius:3}]},
  options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#9a8aaa',font:{size:8}},grid:{display:false},border:{display:false}},y:{min:0,max:100,ticks:{color:'#9a8aaa',font:{size:8},stepSize:25},grid:{color:'#e2e6ef'},border:{display:false}}}}
});
</script>
</body>
</html>"""


@app.get("/demo/coach", response_class=HTMLResponse)
async def demo_coach():
    return DEMO_COACH_HTML


DEMO_STUDENT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbis AI — Student Demo</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--green:#16a34a;--amber:#d97706;--red:#dc2626;--radius:10px;--shadow:0 1px 4px rgba(61,26,110,.08),0 4px 16px rgba(61,26,110,.06);}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);font-size:14px;}
.header{background:var(--navy);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;box-shadow:0 2px 12px rgba(61,26,110,.25);position:sticky;top:0;z-index:100;}
.logo{display:flex;align-items:center;gap:10px;}
.logo-text{font-size:15px;font-weight:700;color:#fff;}.logo-text span{color:var(--lime);}
.logo-sub{font-size:9px;color:rgba(255,255,255,.4);letter-spacing:.14em;text-transform:uppercase;margin-top:1px;}
.demo-badge{background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:4px 12px;font-size:11px;color:var(--lime);font-weight:600;}
.btn-back{background:none;border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.6);border-radius:6px;padding:5px 12px;font-size:11px;cursor:pointer;font-family:inherit;text-decoration:none;}
.main{max-width:1200px;margin:0 auto;padding:24px 20px 60px;}
.welcome{background:var(--navy);border-radius:var(--radius);padding:22px 26px;margin-bottom:20px;border-left:4px solid var(--lime);}
.welcome-title{font-size:18px;font-weight:700;color:#fff;letter-spacing:-.02em;}
.welcome-sub{font-size:13px;color:rgba(255,255,255,.55);margin-top:3px;}
.kpi-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow);}
.kpi-val{font-size:26px;font-weight:700;color:var(--navy);font-family:'DM Mono',monospace;line-height:1;}
.kpi-val.green{color:var(--green);}
.kpi-val.lime{color:var(--lime-dark);}
.kpi-label{font-size:11px;color:var(--text3);margin-top:4px;text-transform:uppercase;letter-spacing:.06em;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;}
.card-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.card-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text2);}
.card-body{padding:16px;}
.skill-row{margin-bottom:12px;}
.skill-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}
.skill-name{font-size:12px;font-weight:500;color:var(--text);}
.skill-scores{display:flex;gap:8px;font-size:11px;}
.score-coach{color:var(--navy);font-weight:600;}
.score-self{color:var(--lime-dark);font-weight:600;}
.skill-bar-bg{height:6px;background:var(--bg);border-radius:3px;position:relative;overflow:hidden;}
.skill-bar-coach{height:100%;background:var(--navy);border-radius:3px;}
.skill-bar-self{height:3px;background:var(--lime);border-radius:3px;position:absolute;top:0;}
.session-row{display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:0.5px solid var(--border);}
.session-row:last-child{border-bottom:none;}
.session-dot{width:8px;height:8px;border-radius:50%;background:var(--lime);margin-top:4px;flex-shrink:0;}
.session-date{font-size:11px;color:var(--text3);min-width:72px;}
.session-text{font-size:12px;color:var(--text2);line-height:1.5;}
.coach-card{display:flex;align-items:center;gap:14px;background:var(--bg);border-radius:8px;padding:14px;margin-bottom:14px;}
.coach-avatar{width:44px;height:44px;border-radius:50%;background:var(--navy);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;color:var(--lime);flex-shrink:0;}
.coach-name{font-size:13px;font-weight:600;color:var(--text);}
.coach-sub{font-size:11px;color:var(--text3);margin-top:2px;}
.next-session{background:linear-gradient(135deg,var(--navy),var(--navy2));border-radius:8px;padding:14px 16px;color:#fff;}
.next-label{font-size:10px;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px;}
.next-date{font-size:15px;font-weight:700;color:#fff;}
.next-focus{font-size:12px;color:rgba(255,255,255,.6);margin-top:4px;}
.connect-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
.connect-btn{display:flex;align-items:center;gap:10px;border-radius:8px;padding:10px 12px;font-family:inherit;width:100%;cursor:pointer;transition:border-color .15s;border:1px solid var(--border);background:var(--bg);}
.connect-btn.connected{border-color:var(--lime);background:var(--lime-pale);}
.connect-icon{font-size:18px;}
.connect-name{font-size:12px;font-weight:500;color:var(--text);text-align:left;}
.connect-status{font-size:10px;margin-top:1px;text-align:left;}
.connect-status.on{color:var(--lime-dark);}
.connect-status.off{color:var(--text3);}
.upload-zone{border:1.5px dashed var(--border);border-radius:8px;padding:18px;text-align:center;cursor:pointer;transition:border-color .15s;margin-bottom:10px;}
.upload-zone:hover{border-color:var(--navy);}
.upload-item{display:flex;align-items:center;gap:8px;background:var(--bg);border-radius:6px;padding:8px 10px;font-size:11px;color:var(--text2);margin-bottom:6px;}
.wearable-data{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px;}
.wdata{background:var(--bg);border-radius:8px;padding:10px 12px;text-align:center;}
.wdata-val{font-size:20px;font-weight:700;font-family:'DM Mono',monospace;color:var(--navy);}
.wdata-val.green{color:var(--green);}
.wdata-label{font-size:10px;color:var(--text3);margin-top:3px;text-transform:uppercase;letter-spacing:.06em;}
.chart-wrap{position:relative;height:90px;}
.toast{position:fixed;top:70px;right:20px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;z-index:999;border-left:3px solid var(--lime);display:none;max-width:280px;line-height:1.5;}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <svg width="28" height="28" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>
    </svg>
    <div>
      <div class="logo-text">Orbis <span>AI</span></div>
      <div class="logo-sub">Student Dashboard</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:10px;">
    <span class="demo-badge">Demo mode</span>
    <a href="/demo/coach" class="btn-back">Coach view</a>
    <a href="/" class="btn-back">Home</a>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="main">

  <div class="welcome">
    <div class="welcome-title">Good morning, Fernando 👋</div>
    <div class="welcome-sub">Roger Lederer Academy · Coach Toni · Recovery 84% — great day to push hard</div>
  </div>

  <div class="kpi-strip">
    <div class="kpi"><div class="kpi-val green">84%</div><div class="kpi-label">Recovery today</div></div>
    <div class="kpi"><div class="kpi-val">57ms</div><div class="kpi-label">HRV</div></div>
    <div class="kpi"><div class="kpi-val lime">4.2</div><div class="kpi-label">Overall skill</div></div>
    <div class="kpi"><div class="kpi-val">6</div><div class="kpi-label">Week streak</div></div>
  </div>

  <div class="grid2">

    <!-- Skills -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">My skills</div>
        <span style="font-size:11px;color:var(--text3)">Jun 15, 2026</span>
      </div>
      <div class="card-body">
        <div style="display:flex;gap:8px;margin-bottom:12px;font-size:11px;">
          <span style="display:flex;align-items:center;gap:4px;color:var(--text3)"><span style="width:8px;height:8px;background:var(--navy);border-radius:50%;display:inline-block;"></span>Coach</span>
          <span style="display:flex;align-items:center;gap:4px;color:var(--text3)"><span style="width:8px;height:8px;background:var(--lime);border-radius:50%;display:inline-block;"></span>Self</span>
        </div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Forehand</div><div class="skill-scores"><span class="score-coach">4.2/5</span><span class="score-self">4.0/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:84%"></div><div class="skill-bar-self" style="width:80%"></div></div></div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Backhand</div><div class="skill-scores"><span class="score-coach">3.5/5</span><span class="score-self">3.2/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:70%"></div><div class="skill-bar-self" style="width:64%"></div></div></div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Serve</div><div class="skill-scores"><span class="score-coach">3.8/5</span><span class="score-self">4.0/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:76%"></div><div class="skill-bar-self" style="width:80%"></div></div></div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Movement</div><div class="skill-scores"><span class="score-coach">4.0/5</span><span class="score-self">3.8/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:80%"></div><div class="skill-bar-self" style="width:76%"></div></div></div>
        <div class="skill-row"><div class="skill-header"><div class="skill-name">Tactical</div><div class="skill-scores"><span class="score-coach">3.2/5</span><span class="score-self">3.0/5</span></div></div><div class="skill-bar-bg"><div class="skill-bar-coach" style="width:64%"></div><div class="skill-bar-self" style="width:60%"></div></div></div>
        <a href="/report/demo" style="display:block;margin-top:14px;background:var(--navy);color:#fff;text-align:center;padding:8px;border-radius:7px;font-size:12px;font-weight:600;text-decoration:none;">View full progress report</a>
      </div>
    </div>

    <!-- Coach + next session -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">My coach</div>
      </div>
      <div class="card-body">
        <div class="coach-card">
          <div class="coach-avatar">T</div>
          <div>
            <div class="coach-name">Coach Toni Alcala</div>
            <div class="coach-sub">Roger Lederer Academy · Madrid</div>
          </div>
        </div>
        <div class="next-session">
          <div class="next-label">Next session</div>
          <div class="next-date">Thursday, Jun 26 — 10:00 AM</div>
          <div class="next-focus">Focus: Backhand slice under pressure + serve consistency</div>
        </div>
        <div style="margin-top:12px;background:rgba(62,207,126,.1);border:1px solid rgba(62,207,126,.25);border-radius:8px;padding:10px 12px;font-size:12px;color:var(--lime-dark);line-height:1.5;">
          Coach note: Great week Fernando. Recovery numbers up — lets push the tactical work Thursday. Keep the pre-match routine tight.
        </div>
      </div>
    </div>

  </div>

  <div class="grid2">

    <!-- Wearable data -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">My devices</div>
        <span style="font-size:11px;color:var(--lime-dark);font-weight:600;">Whoop connected</span>
      </div>
      <div class="card-body">
        <div class="wearable-data">
          <div class="wdata"><div class="wdata-val green">84%</div><div class="wdata-label">Recovery</div></div>
          <div class="wdata"><div class="wdata-val">57ms</div><div class="wdata-label">HRV</div></div>
          <div class="wdata"><div class="wdata-val">7.4h</div><div class="wdata-label">Sleep</div></div>
          <div class="wdata"><div class="wdata-val">52bpm</div><div class="wdata-label">Resting HR</div></div>
          <div class="wdata"><div class="wdata-val">14.2</div><div class="wdata-label">Strain</div></div>
          <div class="wdata"><div class="wdata-val green">95%</div><div class="wdata-label">SpO2</div></div>
        </div>
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text3);margin-bottom:6px;">14-day recovery</div>
        <div class="chart-wrap"><canvas id="wearableChart"></canvas></div>
        <div class="connect-grid" style="margin-top:12px;">
          <button class="connect-btn connected">
            <span class="connect-icon">&#x231A;</span>
            <div><div class="connect-name">Whoop</div><div class="connect-status on">Connected</div></div>
          </button>
          <button class="connect-btn" onclick="showToast('Apple Health connection coming soon')">
            <span class="connect-icon">&#x1F34E;</span>
            <div><div class="connect-name">Apple Health</div><div class="connect-status off">Not connected</div></div>
          </button>
        </div>
      </div>
    </div>

    <!-- Documents -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">My documents</div>
        <span style="font-size:11px;color:var(--text3)">3 uploaded</span>
      </div>
      <div class="card-body">
        <div class="upload-item">
          <span style="font-size:14px;">&#x1F4C4;</span>
          <div>
            <div style="font-size:12px;font-weight:500;color:var(--text);">Whoop_health_report_Jun2026.pdf</div>
            <div style="font-size:10px;color:var(--text3);">Synced to Orbis Core · Jun 20</div>
          </div>
        </div>
        <div class="upload-item">
          <span style="font-size:14px;">&#x1F4CA;</span>
          <div>
            <div style="font-size:12px;font-weight:500;color:var(--text);">Gym_training_plan_Q2.xlsx</div>
            <div style="font-size:10px;color:var(--text3);">Synced to Orbis Core · Jun 15</div>
          </div>
        </div>
        <div class="upload-item">
          <span style="font-size:14px;">&#x1F4DD;</span>
          <div>
            <div style="font-size:12px;font-weight:500;color:var(--text);">Nutrition_plan_May2026.docx</div>
            <div style="font-size:10px;color:var(--text3);">Synced to Orbis Core · May 28</div>
          </div>
        </div>
        <div class="upload-zone" onclick="showToast('Document upload — backend coming soon')">
          <div style="font-size:22px;margin-bottom:6px;">&#x1F4C1;</div>
          <div style="font-size:12px;font-weight:500;color:var(--text2);">Upload a document</div>
          <div style="font-size:10px;color:var(--text3);margin-top:2px;">PDF, Excel, Word — synced to Orbis Core</div>
        </div>
        <div style="margin-top:8px;background:rgba(62,207,126,.08);border:1px solid rgba(62,207,126,.2);border-radius:8px;padding:10px 12px;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--lime-dark);margin-bottom:4px;">Orbis Core insight</div>
          <div style="font-size:11px;color:var(--text2);line-height:1.5;">Your gym plan shows a high volume week — Orbis Core has flagged this against your Whoop recovery data and recommends reducing leg press load by 15% on Thursday.</div>
        </div>
      </div>
    </div>

  </div>

  <!-- Session history -->
  <div class="card">
    <div class="card-header">
      <div class="card-title">Session history</div>
      <span style="font-size:11px;color:var(--text3)">Last 5 sessions</span>
    </div>
    <div class="card-body">
      <div class="session-row"><div class="session-dot"></div><div class="session-date">Jun 20, 2026</div><div class="session-text">Serve and volley drills — 90 min. Recovery 88%. Coach: strong net approach, work on backhand volley placement.</div></div>
      <div class="session-row"><div class="session-dot"></div><div class="session-date">Jun 17, 2026</div><div class="session-text">Match play vs. James — 75 min. Won 6-3 6-4. Recovery 85%. Backhand under pressure improved vs last week.</div></div>
      <div class="session-row"><div class="session-dot"></div><div class="session-date">Jun 15, 2026</div><div class="session-text">Evaluation session — 60 min. Full skill assessment completed. Coach notes: tactical awareness is main improvement area.</div></div>
      <div class="session-row"><div class="session-dot"></div><div class="session-date">Jun 12, 2026</div><div class="session-text">Baseline and cross-court patterns — 90 min. Recovery 79%. Focus on inside-out forehand execution.</div></div>
      <div class="session-row"><div class="session-dot" style="background:var(--amber);"></div><div class="session-date">Jun 10, 2026</div><div class="session-text">Light session — 45 min. Recovery 68% (below threshold). Coach reduced intensity per Whoop data recommendation.</div></div>
    </div>
  </div>

  <!-- Ask Orbis Core -->
  <div style="margin-top:16px;background:var(--navy);border-radius:var(--radius);padding:20px 24px;border-left:4px solid var(--lime);">
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
      <div>
        <div style="font-size:14px;font-weight:700;color:#fff;margin-bottom:4px;">Ask Orbis Core</div>
        <div style="font-size:12px;color:rgba(255,255,255,.55);">Get AI coaching advice, drill suggestions, or mental prep tips — directly on Telegram.</div>
      </div>
      <a href="#" onclick="window.open('https://t.me/orbiscoreai_bot', '_blank'); return false;" style="background:var(--lime);color:var(--navy);font-size:13px;font-weight:700;padding:10px 20px;border-radius:7px;text-decoration:none;white-space:nowrap;">Open Telegram</a>
    </div>
  </div>

</div>

<script>
function showToast(msg){const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';setTimeout(()=>t.style.display='none',3000);}
const d=[72,68,75,80,84,78,82,85,79,83,88,84,80,84];
const l=['Jun 8','Jun 9','Jun 10','Jun 11','Jun 12','Jun 13','Jun 14','Jun 15','Jun 16','Jun 17','Jun 18','Jun 19','Jun 20','Jun 21'];
function rc(v){return v>=75?'#16a34a':v>=55?'#d97706':'#dc2626';}
new Chart(document.getElementById('wearableChart'),{type:'bar',data:{labels:l,datasets:[{data:d,backgroundColor:d.map(v=>rc(v)+'33'),borderColor:d.map(v=>rc(v)),borderWidth:1.5,borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#9a8aaa',font:{size:8}},grid:{display:false},border:{display:false}},y:{min:0,max:100,ticks:{color:'#9a8aaa',font:{size:8},stepSize:25},grid:{color:'#e2e6ef'},border:{display:false}}}}});
</script>
</body>
</html>"""


@app.get("/demo/student", response_class=HTMLResponse)
async def demo_student():
    return DEMO_STUDENT_HTML


DEMO_VIDEO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbis AI — Video Analysis</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--green:#16a34a;--amber:#d97706;--red:#dc2626;--radius:10px;--shadow:0 1px 4px rgba(61,26,110,.08),0 4px 16px rgba(61,26,110,.06);}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);font-size:14px;}
.header{background:var(--navy);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;box-shadow:0 2px 12px rgba(61,26,110,.25);position:sticky;top:0;z-index:100;}
.logo{display:flex;align-items:center;gap:10px;}
.logo-text{font-size:15px;font-weight:700;color:#fff;}.logo-text span{color:var(--lime);}
.logo-sub{font-size:9px;color:rgba(255,255,255,.4);letter-spacing:.14em;text-transform:uppercase;margin-top:1px;}
.demo-badge{background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:4px 12px;font-size:11px;color:var(--lime);font-weight:600;}
.btn-back{background:none;border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.6);border-radius:6px;padding:5px 12px;font-size:11px;cursor:pointer;font-family:inherit;text-decoration:none;}
.main{max-width:1200px;margin:0 auto;padding:24px 20px 60px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;margin-bottom:16px;}
.card-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.card-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text2);}
.card-body{padding:16px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.metric-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:0.5px solid var(--border);}
.metric-row:last-child{border-bottom:none;}
.metric-name{font-size:12px;color:var(--text2);}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;}
.badge-green{background:var(--lime-pale);color:var(--lime-dark);}
.badge-amber{background:#fef3c7;color:#92400e;}
.badge-red{background:#fee2e2;color:#991b1b;}
.upload-zone{border:1.5px dashed var(--border);border-radius:8px;padding:24px;text-align:center;cursor:pointer;transition:border-color .15s;}
.upload-zone:hover{border-color:var(--navy);}
.toast{position:fixed;top:70px;right:20px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;z-index:999;border-left:3px solid var(--lime);display:none;max-width:280px;line-height:1.5;}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <svg width="28" height="28" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/>
      <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>
    </svg>
    <div>
      <div class="logo-text">Orbis <span>AI</span></div>
      <div class="logo-sub">Video Analysis</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:10px;">
    <span class="demo-badge">Demo mode</span>
    <a href="/coach" class="btn-back">&#x2190; Coach dashboard</a>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="main">

  <!-- Header -->
  <div style="background:var(--navy);border-radius:var(--radius);padding:20px 24px;margin-bottom:20px;border-left:4px solid var(--lime);display:flex;align-items:center;justify-content:space-between;">
    <div>
      <div style="font-size:18px;font-weight:700;color:#fff;">Fernando — Backhand analysis</div>
      <div style="font-size:13px;color:rgba(255,255,255,.55);margin-top:3px;">Jun 20, 2026 · 1m 23s · Analyzed by Orbis Core</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="text-align:center;background:rgba(255,255,255,.08);border-radius:8px;padding:10px 16px;">
        <div style="font-size:22px;font-weight:700;color:var(--lime);font-family:'DM Mono',monospace;">3.5</div>
        <div style="font-size:10px;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.06em;">Overall</div>
      </div>
    </div>
  </div>

  <div class="grid2">

    <!-- Left: Court snapshot with annotations -->
    <div>
      <div class="card">
        <div class="card-header">
          <div class="card-title">Session snapshot</div>
          <span style="font-size:11px;color:var(--text3);">Frame 00:14 — contact point</span>
        </div>
        <div class="card-body" style="padding:0;">
          <svg width="100%" viewBox="0 0 500 360" xmlns="http://www.w3.org/2000/svg">
            <!-- Court -->
            <rect width="500" height="360" fill="#c17f3a"/>
            <rect x="36" y="24" width="428" height="312" fill="none" stroke="white" stroke-width="2.5"/>
            <line x1="250" y1="24" x2="250" y2="336" stroke="white" stroke-width="1.5"/>
            <line x1="36" y1="180" x2="464" y2="180" stroke="white" stroke-width="3"/>
            <line x1="36" y1="108" x2="464" y2="108" stroke="white" stroke-width="1.5"/>
            <line x1="36" y1="252" x2="464" y2="252" stroke="white" stroke-width="1.5"/>
            <!-- Net -->
            <rect x="30" y="172" width="440" height="14" fill="#333" rx="2"/>
            <line x1="30" y1="172" x2="470" y2="172" stroke="white" stroke-width="1"/>
            <line x1="30" y1="186" x2="470" y2="186" stroke="white" stroke-width="1"/>
            <rect x="24" y="152" width="10" height="56" fill="#555" rx="2"/>
            <rect x="466" y="152" width="10" height="56" fill="#555" rx="2"/>

            <!-- Player shadow -->
            <ellipse cx="340" cy="304" rx="28" ry="8" fill="rgba(0,0,0,0.3)"/>
            <!-- Legs -->
            <line x1="326" y1="272" x2="314" y2="302" stroke="#2d4a8a" stroke-width="10" stroke-linecap="round"/>
            <line x1="342" y1="270" x2="352" y2="300" stroke="#2d4a8a" stroke-width="10" stroke-linecap="round"/>
            <!-- Shoes -->
            <ellipse cx="312" cy="304" rx="12" ry="5" fill="#fff"/>
            <ellipse cx="354" cy="302" rx="12" ry="5" fill="#fff"/>
            <!-- Body -->
            <rect x="322" y="232" width="34" height="44" rx="8" fill="#3d6abf"/>
            <!-- Head -->
            <circle cx="339" cy="218" r="18" fill="#f5c5a3"/>
            <!-- Hair -->
            <ellipse cx="339" cy="205" rx="17" ry="9" fill="#4a3520"/>
            <!-- Left arm extended back -->
            <line x1="324" y1="244" x2="282" y2="226" stroke="#3d6abf" stroke-width="9" stroke-linecap="round"/>
            <line x1="282" y1="226" x2="252" y2="242" stroke="#f5c5a3" stroke-width="8" stroke-linecap="round"/>
            <!-- Right arm follow through -->
            <line x1="354" y1="244" x2="388" y2="228" stroke="#3d6abf" stroke-width="9" stroke-linecap="round"/>
            <line x1="388" y1="228" x2="410" y2="244" stroke="#f5c5a3" stroke-width="8" stroke-linecap="round"/>
            <!-- Racket -->
            <line x1="252" y1="242" x2="230" y2="255" stroke="#8B6914" stroke-width="5" stroke-linecap="round"/>
            <ellipse cx="218" cy="263" rx="15" ry="20" fill="none" stroke="#8B6914" stroke-width="3"/>
            <ellipse cx="218" cy="263" rx="10" ry="14" fill="none" stroke="#c8a830" stroke-width="1.5"/>
            <line x1="207" y1="256" x2="229" y2="256" stroke="#c8a830" stroke-width="1"/>
            <line x1="206" y1="262" x2="230" y2="262" stroke="#c8a830" stroke-width="1"/>
            <line x1="207" y1="268" x2="229" y2="268" stroke="#c8a830" stroke-width="1"/>
            <line x1="216" y1="248" x2="216" y2="278" stroke="#c8a830" stroke-width="1"/>
            <line x1="220" y1="247" x2="220" y2="279" stroke="#c8a830" stroke-width="1"/>
            <line x1="224" y1="248" x2="224" y2="278" stroke="#c8a830" stroke-width="1"/>
            <!-- Tennis ball -->
            <circle cx="194" cy="260" r="9" fill="#c8e620"/>
            <path d="M186 257 Q194 251 202 257" fill="none" stroke="white" stroke-width="1.5"/>
            <path d="M186 263 Q194 269 202 263" fill="none" stroke="white" stroke-width="1.5"/>

            <!-- AI Annotations -->
            <!-- Contact point - late (red/amber circle) -->
            <circle cx="210" cy="260" r="24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 3"/>
            <line x1="234" y1="248" x2="270" y2="222" stroke="#f59e0b" stroke-width="1.5"/>
            <rect x="270" y="206" width="148" height="22" rx="5" fill="rgba(61,26,110,0.9)"/>
            <text x="278" y="220" fill="#f59e0b" font-size="11" font-family="sans-serif" font-weight="600">&#x26A0; Contact point late</text>

            <!-- Hip rotation annotation -->
            <circle cx="338" cy="258" r="20" fill="none" stroke="#dc2626" stroke-width="2" stroke-dasharray="4 2"/>
            <line x1="318" y1="258" x2="288" y2="278" stroke="#dc2626" stroke-width="1.5"/>
            <rect x="200" y="278" width="100" height="22" rx="5" fill="rgba(61,26,110,0.9)"/>
            <text x="208" y="292" fill="#dc2626" font-size="11" font-family="sans-serif" font-weight="600">&#x2717; Hip rotation</text>

            <!-- Elbow - good (green) -->
            <circle cx="284" cy="228" r="16" fill="none" stroke="#3ecf7e" stroke-width="2" stroke-dasharray="4 2"/>
            <line x1="268" y1="222" x2="240" y2="200" stroke="#3ecf7e" stroke-width="1.5"/>
            <rect x="160" y="182" width="86" height="22" rx="5" fill="rgba(61,26,110,0.9)"/>
            <text x="168" y="196" fill="#3ecf7e" font-size="11" font-family="sans-serif" font-weight="600">Elbow high &#x2713;</text>

            <!-- Footwork - good -->
            <circle cx="334" cy="300" rx="20" r="20" fill="none" stroke="#3ecf7e" stroke-width="2" stroke-dasharray="4 2"/>
            <line x1="334" y1="280" x2="334" y2="264" stroke="#3ecf7e" stroke-width="1.5"/>
            <rect x="286" y="248" width="100" height="22" rx="5" fill="rgba(61,26,110,0.9)"/>
            <text x="294" y="262" fill="#3ecf7e" font-size="11" font-family="sans-serif" font-weight="600">Stance &#x2713;</text>

            <!-- Score badge -->
            <rect x="36" y="30" width="80" height="34" rx="6" fill="rgba(61,26,110,0.9)"/>
            <text x="76" y="44" fill="rgba(255,255,255,0.5)" font-size="9" font-family="sans-serif" text-anchor="middle">TECHNIQUE</text>
            <text x="76" y="58" fill="#3ecf7e" font-size="14" font-family="sans-serif" font-weight="700" text-anchor="middle">3.5 / 5.0</text>

            <!-- Orbis Core badge -->
            <rect x="350" y="30" width="120" height="24" rx="6" fill="rgba(62,207,126,0.15)" stroke="rgba(62,207,126,0.4)" stroke-width="1"/>
            <text x="410" y="45" fill="#3ecf7e" font-size="10" font-family="sans-serif" font-weight="600" text-anchor="middle">Orbis Core analyzed</text>

            <!-- Timestamp -->
            <rect x="36" y="322" width="60" height="18" rx="4" fill="rgba(0,0,0,0.6)"/>
            <text x="66" y="334" fill="#fff" font-size="9" font-family="monospace" text-anchor="middle">00:14 / 01:23</text>
          </svg>
        </div>
      </div>

      <!-- Upload new video -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Upload new video</div>
        </div>
        <div class="card-body">
          <div class="upload-zone" onclick="showToast('Video upload — processing coming soon')">
            <div style="font-size:28px;margin-bottom:8px;">&#x1F4F9;</div>
            <div style="font-size:13px;font-weight:500;color:var(--text2);">Drop video here or click to upload</div>
            <div style="font-size:11px;color:var(--text3);margin-top:4px;">MP4 · MOV · max 500MB</div>
            <div style="margin-top:12px;background:var(--navy);color:#fff;font-size:12px;font-weight:600;padding:8px 20px;border-radius:7px;display:inline-block;">Analyze with Orbis Core</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right: Full analysis -->
    <div>

      <!-- Key finding -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Key finding</div>
          <span style="background:rgba(62,207,126,.12);border:1px solid rgba(62,207,126,.25);border-radius:20px;padding:2px 8px;font-size:10px;color:var(--lime-dark);font-weight:600;">Orbis Core</span>
        </div>
        <div class="card-body">
          <div style="background:var(--navy);border-radius:8px;padding:14px 16px;border-left:3px solid var(--lime);">
            <div style="font-size:13px;color:#fff;line-height:1.6;">Contact point is <strong style="color:var(--lime);">8-12cm too late</strong> on the backhand cross-court. Fernando is making contact behind his front hip rather than in front — reducing pace and causing directional errors under pressure.</div>
          </div>
          <div style="margin-top:10px;background:#fef3c7;border-radius:8px;padding:10px 12px;border-left:3px solid var(--amber);">
            <div style="font-size:11px;font-weight:700;color:#92400e;margin-bottom:3px;">Impact on match stats</div>
            <div style="font-size:12px;color:#78350f;line-height:1.5;">This explains 60-70% of his 22 unforced errors per match. Fixing contact point alone could reduce errors to 16-17/match — bringing him below the 18 target.</div>
          </div>
        </div>
      </div>

      <!-- Technique breakdown -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Technique breakdown</div>
        </div>
        <div class="card-body">
          <div class="metric-row">
            <span class="metric-name">Unit turn / preparation</span>
            <span class="badge badge-green">&#x2713; Good</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Elbow position</span>
            <span class="badge badge-green">&#x2713; Good</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Stance / footwork</span>
            <span class="badge badge-green">&#x2713; Good</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Contact point</span>
            <span class="badge badge-amber">&#x26A0; Late — 8-12cm</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Follow through</span>
            <span class="badge badge-amber">&#x26A0; Shortened</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Hip rotation</span>
            <span class="badge badge-red">&#x2717; Limited</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Racket head speed</span>
            <span class="badge badge-amber">&#x26A0; Below potential</span>
          </div>
        </div>
      </div>

      <!-- ITF drill recommendation -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Drill recommendation</div>
          <span style="font-size:11px;color:var(--text3);">ITF Level 2 framework</span>
        </div>
        <div class="card-body">
          <div style="display:flex;flex-direction:column;gap:10px;">
            <div style="background:var(--lime-pale);border-radius:8px;padding:12px 14px;border-left:3px solid var(--lime-dark);">
              <div style="font-size:11px;font-weight:700;color:var(--lime-dark);margin-bottom:4px;">Drill 1 — Wall contact point fix</div>
              <div style="font-size:12px;color:var(--text);line-height:1.5;">Stand 1m from wall. Hit backhand focusing on contact in front of hip. 3 sets of 20 reps. Immediate feedback from wall bounce confirms contact point.</div>
            </div>
            <div style="background:var(--bg);border-radius:8px;padding:12px 14px;border-left:3px solid var(--navy);">
              <div style="font-size:11px;font-weight:700;color:var(--navy);margin-bottom:4px;">Drill 2 — Cone target backhand</div>
              <div style="font-size:12px;color:var(--text);line-height:1.5;">Place cone 1m in front of baseline. Feed balls forcing Fernando to take contact early. 20 min cross-court drill at medium pace. ITF Level 2 — directional control progression.</div>
            </div>
            <div style="background:var(--bg);border-radius:8px;padding:12px 14px;border-left:3px solid var(--navy);">
              <div style="font-size:11px;font-weight:700;color:var(--navy);margin-bottom:4px;">Drill 3 — Hip rotation activation</div>
              <div style="font-size:12px;color:var(--text);line-height:1.5;">Shadow swing without ball — focus on hip turn leading the swing. 3 sets of 15 reps before court practice. Addresses root cause of shortened follow through.</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Coach note -->
      <div style="background:var(--navy);border-radius:var(--radius);padding:16px 20px;border-left:4px solid var(--lime);">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--lime);margin-bottom:6px;">Orbis Core — Coach recommendation</div>
        <div style="font-size:13px;color:rgba(255,255,255,.85);line-height:1.6;">Thursday session (84% recovery — green light): Start with 15min wall drill, then 20min cone target backhand cross-court. Fernando's match win rate will increase from 69% toward 75%+ as contact point improves and unforced errors drop below 18/match.</div>
      </div>

    </div>
  </div>
</div>

<script>
function showToast(msg){const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';setTimeout(()=>t.style.display='none',3000);}
</script>
</body>
</html>"""


@app.get("/demo/video", response_class=HTMLResponse)
async def demo_video():
    return DEMO_VIDEO_HTML

from mangum import Mangum
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
