# -*- coding: utf-8 -*-
"""
TennisIQ MVP — FastAPI Backend v2
"""

import os
import json
from datetime import date, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
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
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent.parent / "static")), name="static")

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
    with open("static/landing.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/_old_root", response_class=HTMLResponse)
async def _old_root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbis AI — Padel Coaching Intelligence</title>
<meta name="description" content="Orbis AI gives padel coaches an animated tactical simulator, AI video analysis, and a roster built for how padel actually works.">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{font-family:'Inter',system-ui,sans-serif;background:var(--surface);color:var(--text);font-size:15px;line-height:1.5;}
a{text-decoration:none;color:inherit;}

/* ── NAV ── */
.nav{position:sticky;top:0;z-index:100;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-bottom:0.5px solid var(--border);height:64px;display:flex;align-items:center;}
.nav-inner{max-width:1180px;margin:0 auto;width:100%;padding:0 28px;display:flex;align-items:center;justify-content:space-between;}
.nav-logo{display:flex;align-items:center;gap:9px;font-size:16px;font-weight:800;color:var(--text);letter-spacing:-.01em;}
.nav-logo span{color:var(--lime);}
.nav-links{display:flex;align-items:center;gap:28px;font-size:13.5px;color:var(--text2);font-weight:500;}
.nav-links a:hover{color:var(--navy);}
.nav-right{display:flex;align-items:center;gap:14px;}
.nav-signin{font-size:13.5px;color:var(--text2);font-weight:500;}
.nav-cta{background:var(--navy);color:#fff;padding:9px 18px;border-radius:9px;font-size:13px;font-weight:700;transition:background .15s;}
.nav-cta:hover{background:var(--navy2);}

/* ── HERO ── */
.hero{padding:64px 28px 0;text-align:center;background:linear-gradient(180deg,#fff 0%,#fbfaff 100%);}
.hero-inner{max-width:680px;margin:0 auto;}
.hero-badge{display:inline-flex;align-items:center;gap:6px;background:var(--lime-pale);color:var(--lime-dark);font-size:11.5px;font-weight:700;padding:6px 14px;border-radius:20px;margin-bottom:22px;}
.hero-title{font-size:44px;font-weight:800;color:var(--text);line-height:1.12;letter-spacing:-.025em;margin-bottom:18px;}
.hero-title .accent{color:var(--navy);}
.hero-sub{font-size:16.5px;color:var(--text2);line-height:1.6;margin-bottom:30px;max-width:520px;margin-left:auto;margin-right:auto;}
.hero-ctas{display:flex;gap:12px;justify-content:center;margin-bottom:12px;flex-wrap:wrap;}
.btn-pri{background:var(--lime);color:#0a2a16;padding:15px 30px;border-radius:10px;font-size:15px;font-weight:700;transition:background .15s;display:inline-block;}
.btn-pri:hover{background:#34b86c;}
.btn-sec{background:#fff;color:var(--navy);padding:15px 30px;border-radius:10px;font-size:15px;font-weight:700;border:1.5px solid var(--navy);transition:all .15s;display:inline-block;}
.btn-sec:hover{background:var(--bg);}
.hero-fine{font-size:12px;color:var(--text3);margin-bottom:48px;}

/* ── HERO VISUAL (animated simulator) ── */
.hero-visual{padding:0 28px 64px;display:flex;justify-content:center;}
.sim-frame{background:#fff;border:1px solid var(--border);border-radius:18px;box-shadow:0 24px 70px rgba(61,26,110,.16);overflow:hidden;max-width:740px;width:100%;}
.sim-topbar{background:var(--navy);height:42px;display:flex;align-items:center;justify-content:space-between;padding:0 18px;}
.sim-topbar-l{display:flex;align-items:center;gap:8px;}
.sim-dot{width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.3);}
.sim-label{font-size:12px;font-weight:600;color:rgba(255,255,255,.8);margin-left:8px;}
.sim-badge{background:rgba(62,207,126,.18);color:var(--lime);font-size:10.5px;font-weight:700;padding:4px 11px;border-radius:20px;}
.sim-court{background:#1a4d7a;position:relative;overflow:hidden;}
.sim-caption{padding:14px 18px;background:#fff;border-top:0.5px solid var(--border);font-size:12.5px;color:var(--text2);text-align:center;font-weight:500;}
.sim-caption b{color:var(--text);}

/* ── PROBLEM SECTION ── */
.problem{background:var(--bg);padding:72px 28px;}
.section-inner{max-width:1080px;margin:0 auto;}
.section-eyebrow{font-size:12px;font-weight:700;color:var(--lime-dark);text-transform:uppercase;letter-spacing:.08em;text-align:center;margin-bottom:10px;}
.section-title{font-size:30px;font-weight:800;color:var(--text);text-align:center;letter-spacing:-.015em;margin-bottom:44px;line-height:1.25;}
.problem-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;}
.problem-card{background:#fff;border:1px solid var(--border);border-radius:14px;padding:24px;}
.problem-icon{width:38px;height:38px;border-radius:9px;background:#fef2f2;display:flex;align-items:center;justify-content:center;margin-bottom:14px;font-size:18px;}
.problem-ptitle{font-size:15px;font-weight:700;color:var(--text);margin-bottom:8px;}
.problem-pdesc{font-size:13px;color:var(--text2);line-height:1.6;margin-bottom:14px;}
.problem-fix{display:flex;align-items:center;gap:7px;font-size:12.5px;font-weight:600;color:var(--lime-dark);}
.problem-fix-dot{width:6px;height:6px;border-radius:50%;background:var(--lime);}

/* ── TOOLS SHOWCASE ── */
.tools{background:#fff;padding:80px 28px;}
.tools-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:980px;margin:0 auto;}
.tool-card{border-radius:18px;overflow:hidden;min-height:280px;display:flex;flex-direction:column;justify-content:flex-end;padding:28px 30px;position:relative;cursor:pointer;transition:transform .2s;}
.tool-card:hover{transform:translateY(-3px);}
.tool-card.sim{background:linear-gradient(135deg,#1a5c38 0%,#0d2818 100%);}
.tool-card.vid{background:linear-gradient(135deg,#2a0f52 0%,#1a0a2e 100%);}
.tool-icon-wrap{width:46px;height:46px;border-radius:12px;background:rgba(255,255,255,.1);display:flex;align-items:center;justify-content:center;margin-bottom:16px;font-size:22px;}
.tool-badge{position:absolute;top:20px;right:20px;background:rgba(62,207,126,.18);border:1px solid rgba(62,207,126,.4);color:var(--lime);font-size:10.5px;font-weight:700;padding:4px 11px;border-radius:20px;}
.tool-title{font-size:21px;font-weight:800;color:#fff;margin-bottom:8px;letter-spacing:-.01em;}
.tool-desc{font-size:13.5px;color:rgba(255,255,255,.62);line-height:1.6;max-width:380px;margin-bottom:16px;}
.tool-cta{font-size:13px;font-weight:700;color:var(--lime);}

/* ── WHY ORBIS ── */
.why{background:var(--bg);padding:80px 28px;}
.why-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;max-width:1080px;margin:0 auto 40px;}
.why-card{background:#fff;border:1px solid var(--border);border-radius:14px;padding:26px;}
.why-icon{width:36px;height:36px;border-radius:9px;background:var(--lime-pale);display:flex;align-items:center;justify-content:center;margin-bottom:16px;font-size:17px;}
.why-title{font-size:15.5px;font-weight:700;color:var(--text);margin-bottom:9px;}
.why-desc{font-size:13px;color:var(--text2);line-height:1.65;}

/* ── COACH-SUBMITTED TACTICS ── */
.creator{background:#fff;padding:0 28px 80px;}
.creator-card{max-width:1080px;margin:0 auto;background:linear-gradient(135deg,var(--navy) 0%,#2a0f52 100%);border-radius:20px;padding:48px 50px;display:grid;grid-template-columns:1.1fr 1fr;gap:40px;align-items:center;}
.creator-eyebrow{font-size:11.5px;font-weight:700;color:var(--lime);text-transform:uppercase;letter-spacing:.07em;margin-bottom:14px;}
.creator-title{font-size:26px;font-weight:800;color:#fff;line-height:1.25;letter-spacing:-.01em;margin-bottom:14px;}
.creator-desc{font-size:14px;color:rgba(255,255,255,.65);line-height:1.65;margin-bottom:20px;}
.creator-reward{display:inline-flex;align-items:center;gap:9px;background:rgba(62,207,126,.12);border:1px solid rgba(62,207,126,.3);border-radius:10px;padding:11px 16px;font-size:13px;color:var(--lime);font-weight:600;}
.creator-visual{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:20px;}
.creator-row{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.08);}
.creator-row:last-child{border-bottom:none;}
.creator-rname{font-size:12.5px;font-weight:600;color:#fff;flex:1;}
.creator-rstatus{font-size:9.5px;font-weight:700;padding:3px 9px;border-radius:20px;}
.creator-rstatus.approved{background:rgba(62,207,126,.15);color:var(--lime);}
.creator-rstatus.pending{background:rgba(245,158,11,.15);color:#fbbf24;}

/* ── COMPARISON ── */
.compare{background:var(--bg);padding:80px 28px;}
.ctable{max-width:680px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;border:0.5px solid var(--border);}
.crow{display:grid;grid-template-columns:1fr 100px 100px;align-items:center;padding:13px 22px;border-bottom:0.5px solid var(--border);font-size:13.5px;}
.crow:last-child{border-bottom:none;}
.crow.head{background:var(--navy);color:#fff;font-weight:700;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;}
.crow.head div:not(:first-child){text-align:center;}
.crow div:not(:first-child){text-align:center;font-weight:700;font-size:15px;}
.c-yes{color:var(--lime-dark);}
.c-no{color:#d4cfe8;}

/* ── FOOTER CTA ── */
.footer-cta{background:#fff;padding:80px 28px;text-align:center;}
.footer-cta-title{font-size:30px;font-weight:800;color:var(--text);letter-spacing:-.015em;margin-bottom:14px;}
.footer-cta-sub{font-size:14.5px;color:var(--text2);margin-bottom:28px;}

/* ── FOOTER ── */
.footer{background:var(--navy);padding:48px 28px 32px;}
.footer-inner{max-width:1080px;margin:0 auto;display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:40px;}
.footer-logo{display:flex;align-items:center;gap:9px;font-size:16px;font-weight:800;color:#fff;margin-bottom:10px;}
.footer-logo span{color:var(--lime);}
.footer-desc{font-size:12.5px;color:rgba(255,255,255,.5);line-height:1.6;max-width:280px;}
.footer-col-title{font-size:11px;font-weight:700;color:rgba(255,255,255,.4);text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;}
.footer-link{display:block;font-size:13px;color:rgba(255,255,255,.65);margin-bottom:10px;}
.footer-link:hover{color:#fff;}
.footer-bottom{max-width:1080px;margin:36px auto 0;padding-top:24px;border-top:1px solid rgba(255,255,255,.1);display:flex;justify-content:space-between;font-size:12px;color:rgba(255,255,255,.4);}

/* ── WAITLIST MODAL (reuse existing structure) ── */
.wl-overlay{display:none;position:fixed;inset:0;background:rgba(26,10,46,.5);backdrop-filter:blur(3px);z-index:1000;align-items:center;justify-content:center;padding:20px;}
.wl-overlay.open{display:flex;}
.wl-box{background:#fff;border-radius:18px;max-width:440px;width:100%;max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(61,26,110,.3);}
.wl-header{background:var(--navy);padding:22px 26px;border-radius:18px 18px 0 0;display:flex;align-items:center;justify-content:space-between;}
.wl-title{font-size:16px;font-weight:800;color:#fff;}
.wl-close{cursor:pointer;color:rgba(255,255,255,.55);font-size:20px;background:none;border:none;}
.wl-close:hover{color:#fff;}
.wl-body{padding:24px 26px;}
.wl-field{margin-bottom:14px;}
.wl-label{font-size:12px;font-weight:600;color:var(--text);margin-bottom:6px;display:block;}
.wl-input,.wl-select{width:100%;border:1px solid var(--border);border-radius:9px;padding:10px 13px;font-size:13.5px;font-family:inherit;outline:none;}
.wl-input:focus,.wl-select:focus{border-color:var(--navy);}
.wl-submit{width:100%;background:var(--lime);color:#0a2a16;font-size:14px;font-weight:700;padding:13px;border-radius:10px;border:none;cursor:pointer;margin-top:6px;}
.wl-submit:hover{background:#34b86c;}
.wl-fine{font-size:11.5px;color:var(--text3);text-align:center;margin-top:10px;}
.wl-success{display:none;text-align:center;padding:20px 10px;}
.wl-success.show{display:block;}
.wl-success-icon{font-size:40px;margin-bottom:14px;}

@media (max-width:860px){
  .nav-links{display:none;}
  .hero-title{font-size:32px;}
  .problem-grid,.why-grid{grid-template-columns:1fr;}
  .tools-grid{grid-template-columns:1fr;}
  .creator-card{grid-template-columns:1fr;}
  .footer-inner{grid-template-columns:1fr;gap:28px;}
}
</style>
</head>
<body>
<div class="nav">
  <div class="nav-inner">
    <div class="nav-logo">
      <svg width="22" height="22" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/><path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/></svg>
      Orbis <span>AI</span>
    </div>
    <div class="nav-links">
      <a href="#simulator">Simulator</a>
      <a href="#video">Video analysis</a>
      <a href="#why">Why Orbis</a>
      <a href="/demo/coach">See live demo</a>
    </div>
    <div class="nav-right">
      <a href="/login" class="nav-signin">Sign in</a>
      <a href="#" class="nav-cta" onclick="openWaitlist();return false;">Join waitlist</a>
    </div>
  </div>
</div>

<div class="hero">
  <div class="hero-inner">
    <div class="hero-badge">For padel coaches</div>
    <div class="hero-title">Stop drawing plays on a napkin.<br>Show them <span class="accent">animated.</span></div>
    <div class="hero-sub">Orbis AI gives padel coaches an animated tactical simulator, AI video analysis, and a roster built for how padel academies actually run.</div>
    <div class="hero-ctas">
      <a href="#" class="btn-pri" onclick="openWaitlist();return false;">Join waitlist &rarr;</a>
      <a href="/demo/coach" class="btn-sec">See live demo</a>
    </div>
    <div class="hero-fine">Free early access &middot; No credit card &middot; Limited spots</div>
  </div>
</div>

<div class="hero-visual" id="simulator">
  <div class="sim-frame">
    <div class="sim-topbar">
      <div class="sim-topbar-l">
        <div class="sim-dot"></div><div class="sim-dot"></div><div class="sim-dot"></div>
        <div class="sim-label">Orbis AI &middot; Tactical simulator</div>
      </div>
      <div class="sim-badge">+300 plays</div>
    </div>
    <div class="sim-court">
      <canvas id="heroCanvas" style="display:block;width:100%;"></canvas>
    </div>
    <div class="sim-caption">Watch your students learn <b>serve + net rush</b> in seconds, not sentences</div>
  </div>
</div>

<div class="problem">
  <div class="section-inner">
    <div class="section-eyebrow">The problem</div>
    <div class="section-title">Great coaches lose hours<br>to tools that weren't built for padel.</div>
    <div class="problem-grid">

      <div class="problem-card">
        <div class="problem-icon">&#128221;</div>
        <div class="problem-ptitle">Excel and WhatsApp don't scale</div>
        <div class="problem-pdesc">Tracking 10+ students across categor&iacute;as, recurrence, and class type in spreadsheets means something always slips through.</div>
        <div class="problem-fix"><div class="problem-fix-dot"></div>Orbis keeps your whole roster organized</div>
      </div>

      <div class="problem-card">
        <div class="problem-icon">&#127934;</div>
        <div class="problem-ptitle">Explaining a play takes forever</div>
        <div class="problem-pdesc">Describing a bandeja-to-vibora sequence in words, or sketching it on a whiteboard, loses students before the point even lands.</div>
        <div class="problem-fix"><div class="problem-fix-dot"></div>Orbis animates the play in seconds</div>
      </div>

      <div class="problem-card">
        <div class="problem-icon">&#128064;</div>
        <div class="problem-ptitle">No record of what improved</div>
        <div class="problem-pdesc">Students ask "am I getting better?" and you're relying on memory instead of a real evaluation history.</div>
        <div class="problem-fix"><div class="problem-fix-dot"></div>Orbis tracks every session</div>
      </div>

    </div>
  </div>
</div>

<div class="tools">
  <div class="section-inner">
    <div class="section-eyebrow">The platform</div>
    <div class="section-title">Your two best coaching tools</div>
    <div class="tools-grid">

      <a href="/demo/simulator" class="tool-card sim">
        <div class="tool-badge">+300 plays</div>
        <div class="tool-icon-wrap">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3ecf7e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
        </div>
        <div class="tool-title">Tactical simulator</div>
        <div class="tool-desc">Animated padel plays grounded in FIP Academy &mdash; show students exactly how a point should unfold, from beginner to advanced.</div>
        <div class="tool-cta">Open simulator &rarr;</div>
      </a>

      <a href="/demo/video" class="tool-card vid">
        <div class="tool-badge">Orbis Core analyzed</div>
        <div class="tool-icon-wrap">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
        </div>
        <div class="tool-title">Video analysis</div>
        <div class="tool-desc">Upload a session clip &mdash; Orbis Core breaks down split-step timing, paddle position, and weight transfer with FIP drill fixes.</div>
        <div class="tool-cta">Open video analysis &rarr;</div>
      </a>

    </div>
  </div>
</div>

<div class="why" id="why">
  <div class="section-inner">
    <div class="section-eyebrow">Why Orbis AI</div>
    <div class="section-title">Not a generic tool with a padel skin.</div>
    <div class="why-grid">

      <div class="why-card">
        <div class="why-icon">&#129504;</div>
        <div class="why-title">AI agent intelligence</div>
        <div class="why-desc">Orbis Core is a conversational AI agent that knows your students and gives actionable recommendations &mdash; not generic tips copied from a fitness app.</div>
      </div>

      <div class="why-card">
        <div class="why-icon">&#127942;</div>
        <div class="why-title">Real FIP Academy framework</div>
        <div class="why-desc">Every drill recommendation and tactical play is grounded in FIP Academy Level 0-4 &mdash; the actual coaching standard for padel, not invented content.</div>
      </div>

      <div class="why-card">
        <div class="why-icon">&#127934;</div>
        <div class="why-title">Built padel-first</div>
        <div class="why-desc">No dedicated coaching software exists for padel today. We built the tactical simulator, video analysis, and roster specifically for how padel is taught.</div>
      </div>

    </div>
  </div>
</div>

<div class="creator">
  <div class="creator-card">
    <div>
      <div class="creator-eyebrow">Built with coaches, not just for them</div>
      <div class="creator-title">Submit your own tactics. Orbis brings them to life.</div>
      <div class="creator-desc">Describe a rally in your own words and Orbis Core builds the animation. Once approved, it joins the +300 plays library &mdash; and every coach who uses it puts money in your pocket.</div>
      <div class="creator-reward">
        <span>&#128176;</span>
        <span>5 euros for every 1,000 times your tactic gets used</span>
      </div>
    </div>
    <div class="creator-visual">
      <div class="creator-row">
        <div class="creator-rname">Fake bandeja, real chiquita</div>
        <div class="creator-rstatus approved">Approved</div>
      </div>
      <div class="creator-row">
        <div class="creator-rname">Cross vibora into the glass</div>
        <div class="creator-rstatus pending">Pending</div>
      </div>
      <div class="creator-row">
        <div class="creator-rname">Double lob recovery</div>
        <div class="creator-rstatus pending">In review</div>
      </div>
    </div>
  </div>
</div>

<div class="compare" id="video">
  <div class="section-inner">
    <div class="section-eyebrow">Comparison</div>
    <div class="section-title">Others manage courts.<br>We coach padel.</div>
    <div class="ctable">
      <div class="crow head"><div>Feature</div><div>Orbis AI</div><div>Others</div></div>
      <div class="crow"><div>Animated tactical plays</div><div class="c-yes">&#10003;</div><div class="c-no">&#10005;</div></div>
      <div class="crow"><div>FIP Academy framework built-in</div><div class="c-yes">&#10003;</div><div class="c-no">&#10005;</div></div>
      <div class="crow"><div>AI video technique analysis</div><div class="c-yes">&#10003;</div><div class="c-no">&#10005;</div></div>
      <div class="crow"><div>Coach-submitted tactics + rewards</div><div class="c-yes">&#10003;</div><div class="c-no">&#10005;</div></div>
      <div class="crow"><div>Student roster with categor&iacute;a tags</div><div class="c-yes">&#10003;</div><div class="c-no">&#10005;</div></div>
      <div class="crow"><div>Per-session evaluations</div><div class="c-yes">&#10003;</div><div class="c-no">&#10005;</div></div>
      <div class="crow"><div>Built padel-first, not adapted</div><div class="c-yes">&#10003;</div><div class="c-no">&#10005;</div></div>
    </div>
  </div>
</div>

<div class="footer-cta">
  <div class="footer-cta-title">Ready to coach smarter?</div>
  <div class="footer-cta-sub">Join the waiting list &mdash; early access opens soon for padel coaches in Europe and LatAm.</div>
  <a href="#" class="btn-pri" onclick="openWaitlist();return false;">Join waitlist &rarr;</a>
</div>

<div class="footer">
  <div class="footer-inner">
    <div>
      <div class="footer-logo">
        <svg width="22" height="22" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/><path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/></svg>
        Orbis <span>AI</span>
      </div>
      <div class="footer-desc">Padel coaching intelligence. Built for coaches who want to win.</div>
    </div>
    <div>
      <div class="footer-col-title">Demo</div>
      <a href="/demo/coach" class="footer-link">Coach hub</a>
      <a href="/demo/simulator" class="footer-link">Tactical simulator</a>
      <a href="/demo/video" class="footer-link">Video analysis</a>
    </div>
    <div>
      <div class="footer-col-title">Platform</div>
      <a href="/login" class="footer-link">Sign in</a>
      <a href="/register" class="footer-link">Register</a>
      <a href="https://t.me/orbiscoreai_bot" class="footer-link">Orbis Core bot</a>
    </div>
  </div>
  <div class="footer-bottom">
    <div>&copy; 2026 Orbis AI. All rights reserved.</div>
    <div>Madrid, Spain &middot; Padel Coaching Intelligence</div>
  </div>
</div>

<div class="wl-overlay" id="waitlistModal">
  <div class="wl-box">
    <div class="wl-header">
      <div class="wl-title">Join the waiting list</div>
      <button class="wl-close" onclick="closeWaitlist()">&#10005;</button>
    </div>
    <div class="wl-body">

      <div id="wlForm">
        <p style="font-size:13px;color:var(--text2);margin-bottom:18px;line-height:1.55;">Be among the first padel coaches to get access. We're onboarding in Europe and LatAm.</p>
        <div class="wl-field">
          <label class="wl-label">Full name</label>
          <input class="wl-input" id="wlName" placeholder="Your name">
        </div>
        <div class="wl-field">
          <label class="wl-label">Email</label>
          <input class="wl-input" id="wlEmail" type="email" placeholder="you@email.com">
        </div>
        <div class="wl-field">
          <label class="wl-label">Country</label>
          <input class="wl-input" id="wlCountry" placeholder="Spain">
        </div>
        <div class="wl-field">
          <label class="wl-label">City</label>
          <input class="wl-input" id="wlCity" placeholder="Madrid">
        </div>
        <button class="wl-submit" id="wlSubmitBtn" onclick="submitWaitlist()">Join waiting list &rarr;</button>
        <div class="wl-fine">Free early access &middot; No credit card required</div>
      </div>

      <div class="wl-success" id="wlSuccess">
        <div class="wl-success-icon">&#9989;</div>
        <div style="font-size:16px;font-weight:700;color:var(--text);margin-bottom:8px;">You're on the list!</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.6;">We'll reach out as soon as early access opens in your region. Thank you for joining Orbis AI.</div>
      </div>

    </div>
  </div>
</div>

<script>
function openWaitlist(){document.getElementById('waitlistModal').classList.add('open');}
function closeWaitlist(){document.getElementById('waitlistModal').classList.remove('open');}

async function submitWaitlist(){
  const name=document.getElementById('wlName').value.trim();
  const email=document.getElementById('wlEmail').value.trim();
  const country=document.getElementById('wlCountry').value.trim();
  const city=document.getElementById('wlCity').value.trim();
  if(!name||!email){alert('Please enter your name and email.');return;}
  const btn=document.getElementById('wlSubmitBtn');
  btn.disabled=true;btn.textContent='Saving...';
  try{
    const res=await fetch('/api/waitlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,email,country,city,sport:'padel'})});
    if(res.ok){
      document.getElementById('wlForm').style.display='none';
      document.getElementById('wlSuccess').classList.add('show');
    } else {
      btn.disabled=false;btn.textContent='Join waiting list \u2192';
      alert('Something went wrong. Please try again.');
    }
  }catch(e){
    btn.disabled=false;btn.textContent='Join waiting list \u2192';
    alert('Network error. Please try again.');
  }
}

(function(){
  const canvas = document.getElementById('heroCanvas');
  if(!canvas)return;
  const ctx = canvas.getContext('2d');
  let CW, CH;

  function setup(){
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.parentElement.clientWidth;
    const h = Math.round(w * 0.55);
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(dpr,0,0,dpr,0,0);
    CW = w; CH = h;
  }

  function sc(nx, ny){
    const tLx = CW*0.25, tRx = CW*0.75, tY = CH*0.08;
    const bLx = CW*0.06, bRx = CW*0.94, bY = CH*0.92;
    const lx = tLx + (bLx-tLx)*ny, rx = tRx + (bRx-tRx)*ny;
    const px = lx + (rx-lx)*nx;
    const py = tY + (bY-tY)*ny;
    return {x:px, y:py};
  }

  function bez(p0,p1,p2,t){
    return {x:(1-t)*(1-t)*p0.x+2*(1-t)*t*p1.x+t*t*p2.x, y:(1-t)*(1-t)*p0.y+2*(1-t)*t*p1.y+t*t*p2.y};
  }
  function ease(t){return t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;}
  function lerp(a,b,t){return a+(b-a)*t;}

  function drawCourt(){
    const tLx = CW*0.25, tRx = CW*0.75, tY = CH*0.08;
    const bLx = CW*0.06, bRx = CW*0.94, bY = CH*0.92;
    ctx.fillStyle = '#1a4d7a';
    ctx.fillRect(0,0,CW,CH);
    ctx.beginPath();
    ctx.moveTo(tLx,tY); ctx.lineTo(tRx,tY); ctx.lineTo(bRx,bY); ctx.lineTo(bLx,bY); ctx.closePath();
    ctx.fillStyle = '#2e6cb0';
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.85)';
    ctx.lineWidth = 2;
    ctx.stroke();
    const nL = sc(0,0.5), nR = sc(1,0.5);
    ctx.beginPath(); ctx.moveTo(nL.x,nL.y); ctx.lineTo(nR.x,nR.y);
    ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 2.5; ctx.stroke();
    const sL1=sc(0,0.15), sR1=sc(1,0.15), sL2=sc(0,0.85), sR2=sc(1,0.85);
    ctx.strokeStyle='rgba(255,255,255,0.4)'; ctx.lineWidth=1.2;
    ctx.beginPath();ctx.moveTo(sL1.x,sL1.y);ctx.lineTo(sR1.x,sR1.y);ctx.stroke();
    ctx.beginPath();ctx.moveTo(sL2.x,sL2.y);ctx.lineTo(sR2.x,sR2.y);ctx.stroke();
    const cN=sc(.5,.5), cS1=sc(.5,.15), cS2=sc(.5,.85);
    ctx.strokeStyle='rgba(255,255,255,0.3)'; ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(cS1.x,cS1.y);ctx.lineTo(cN.x,cN.y);ctx.stroke();
    ctx.beginPath();ctx.moveTo(cN.x,cN.y);ctx.lineTo(cS2.x,cS2.y);ctx.stroke();
  }

  function drawPlayer(nx,ny,fill,ring,label){
    const p = sc(nx,ny);
    const r = CW*(0.022+ny*0.018);
    const bodyH = r*1.6;
    ctx.beginPath();
    ctx.ellipse(p.x,p.y+r*0.25,r*0.9,r*0.32,0,0,Math.PI*2);
    ctx.fillStyle='rgba(0,0,0,0.4)'; ctx.fill();
    ctx.beginPath();
    ctx.moveTo(p.x-r,p.y);ctx.lineTo(p.x+r,p.y);
    ctx.lineTo(p.x+r*0.9,p.y-bodyH);ctx.lineTo(p.x-r*0.9,p.y-bodyH);
    ctx.closePath(); ctx.fillStyle=fill; ctx.fill();
    ctx.beginPath();
    ctx.ellipse(p.x,p.y-bodyH,r*0.9,r*0.32,0,0,Math.PI*2);
    ctx.fillStyle=ring; ctx.fill();
    ctx.fillStyle='rgba(255,255,255,0.95)';
    ctx.font='bold '+Math.round(r*0.7)+'px Inter,sans-serif';
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(label,p.x,p.y-bodyH+r*0.08);
  }

  function drawBall(nx,ny,h){
    const p = sc(nx,ny);
    const lift = h*CH*0.18;
    const r = CW*0.016+h*CW*0.011;
    ctx.beginPath();
    ctx.ellipse(p.x,p.y,r*0.9,r*0.32,0,0,Math.PI*2);
    ctx.fillStyle='rgba(0,0,0,0.35)'; ctx.fill();
    ctx.beginPath();
    ctx.arc(p.x,p.y-lift,r,0,Math.PI*2);
    ctx.fillStyle='#d4e820'; ctx.fill();
    ctx.strokeStyle='#9aac00'; ctx.lineWidth=1; ctx.stroke();
  }

  const sequence = [
    {f:{x:.68,y:.88},c:{x:.5,y:.65},t:{x:.5,y:.12},ht:.18,d:1300,
     yA:[{x:.32,y:.88},{x:.68,y:.88}],yB:[{x:.32,y:.88},{x:.68,y:.88}],
     oA:[{x:.28,y:.14},{x:.72,y:.14}],oB:[{x:.28,y:.14},{x:.72,y:.14}]},
    {move:true,d:1100,
     yA:[{x:.32,y:.88},{x:.68,y:.88}],yB:[{x:.32,y:.57},{x:.68,y:.57}],
     oA:[{x:.28,y:.14},{x:.72,y:.14}],oB:[{x:.28,y:.14},{x:.72,y:.14}]},
    {f:{x:.28,y:.14},c:{x:.55,y:.4},t:{x:.65,y:.62},ht:.12,d:1100,
     yA:[{x:.32,y:.57},{x:.68,y:.57}],yB:[{x:.32,y:.57},{x:.68,y:.57}],
     oA:[{x:.28,y:.14},{x:.72,y:.14}],oB:[{x:.28,y:.14},{x:.72,y:.14}]},
    {f:{x:.65,y:.6},c:{x:.4,y:.35},t:{x:.15,y:.1},ht:.06,d:850,winner:true,
     yA:[{x:.32,y:.57},{x:.68,y:.57}],yB:[{x:.32,y:.57},{x:.68,y:.57}],
     oA:[{x:.28,y:.14},{x:.72,y:.14}],oB:[{x:.28,y:.14},{x:.72,y:.14}]},
    {pause:true,d:1400,
     yA:[{x:.32,y:.57},{x:.68,y:.57}],yB:[{x:.32,y:.57},{x:.68,y:.57}],
     oA:[{x:.28,y:.14},{x:.72,y:.14}],oB:[{x:.28,y:.14},{x:.72,y:.14}]}
  ];

  let step = 0, stepStart = null;

  function render(t){
    ctx.clearRect(0,0,CW,CH);
    drawCourt();
    const s = sequence[step];
    const et = ease(Math.min(t,1));
    const py = s.yA.map((p,i)=>({x:lerp(p.x,s.yB[i].x,et), y:lerp(p.y,s.yB[i].y,et)}));
    const po = s.oA.map((p,i)=>({x:lerp(p.x,s.oB[i].x,et), y:lerp(p.y,s.oB[i].y,et)}));
    po.forEach((p,i)=>drawPlayer(p.x,p.y,'#50000e','#dc2626',['O1','O2'][i]));
    py.forEach((p,i)=>drawPlayer(p.x,p.y,'#1a0a2e',i===1?'#3ecf7e':'#7c4de0',['Y1','Y2'][i]));
    if(s.f && !s.move){
      const bp = bez(s.f, s.c, s.t, et);
      const h = (s.ht||0)*Math.sin(et*Math.PI);
      drawBall(bp.x, bp.y, h);
    } else if(s.move || s.pause){
      const last = sequence[step===0?sequence.length-1:step-1];
      if(last && last.t) drawBall(last.t.x, last.t.y, 0);
    }
    if(s.winner && t>0.85){
      ctx.fillStyle='rgba(245,158,11,0.95)';
      ctx.font='bold '+Math.round(CW*0.024)+'px Inter,sans-serif';
      ctx.textAlign='center';
      ctx.fillText('WINNER',CW*0.18,CH*0.18);
    }
  }

  function loop(ts){
    const s = sequence[step];
    if(!stepStart) stepStart = ts;
    const dur = s.d || 1000;
    const t = (ts - stepStart) / dur;
    render(Math.min(t,1));
    if(t >= 1){
      step = (step+1) % sequence.length;
      stepStart = null;
    }
    requestAnimationFrame(loop);
  }

  setup();
  window.addEventListener('resize', setup);
  requestAnimationFrame(loop);
})();
</script>

</body>
</html>
"""

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
<title>Orbis AI — Padel Coach Hub</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--green:#16a34a;--amber:#d97706;--red:#dc2626;--radius:12px;--shadow:0 1px 4px rgba(61,26,110,.08),0 4px 16px rgba(61,26,110,.06);}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);font-size:14px;}
.header{background:var(--navy);height:60px;display:flex;align-items:center;justify-content:space-between;padding:0 28px;box-shadow:0 2px 12px rgba(61,26,110,.25);position:sticky;top:0;z-index:100;}
.logo{display:flex;align-items:center;gap:10px;}
.logo-text{font-size:16px;font-weight:800;color:#fff;letter-spacing:-.02em;}
.logo-text span{color:var(--lime);}
.logo-sub{font-size:9px;color:rgba(255,255,255,.45);letter-spacing:.14em;text-transform:uppercase;margin-top:1px;}
.header-right{display:flex;align-items:center;gap:12px;}
.coach-chip{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);border-radius:20px;padding:5px 14px;font-size:12px;color:rgba(255,255,255,.85);display:flex;align-items:center;gap:6px;}
.coach-chip .dot{width:6px;height:6px;border-radius:50%;background:var(--lime);}
.btn-logout{background:none;border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.6);border-radius:7px;padding:6px 14px;font-size:12px;cursor:pointer;font-family:inherit;}

.main{max-width:1280px;margin:0 auto;padding:24px 24px 60px;}

.welcome{margin-bottom:22px;}
.welcome-title{font-size:22px;font-weight:800;color:var(--text);letter-spacing:-.02em;}
.welcome-sub{font-size:13px;color:var(--text2);margin-top:3px;}

/* ── HERO: Simulator + Video Analysis (the moat) ── */
.hero-row{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:28px;}
.hero-card{position:relative;border-radius:18px;overflow:hidden;cursor:pointer;min-height:200px;display:flex;flex-direction:column;justify-content:flex-end;padding:22px 24px;box-shadow:0 8px 32px rgba(61,26,110,.16);transition:transform .2s,box-shadow .2s;}
.hero-card:hover{transform:translateY(-3px);box-shadow:0 14px 40px rgba(61,26,110,.22);}
.hero-card.simulator{background:linear-gradient(135deg,#1a5c38 0%,#0d2818 100%);}
.hero-card.video{background:linear-gradient(135deg,#2a0f52 0%,#1a0a2e 100%);}
.hero-bg-pattern{position:absolute;inset:0;opacity:.5;}
.hero-badge-new{position:absolute;top:18px;right:18px;background:rgba(62,207,126,.18);border:1px solid rgba(62,207,126,.4);color:var(--lime);font-size:10px;font-weight:700;padding:4px 10px;border-radius:20px;letter-spacing:.04em;text-transform:uppercase;}
.hero-icon-wrap{width:46px;height:46px;border-radius:12px;background:rgba(255,255,255,.1);display:flex;align-items:center;justify-content:center;margin-bottom:14px;backdrop-filter:blur(4px);}
.hero-icon-wrap svg{width:24px;height:24px;}
.hero-card-title{font-size:19px;font-weight:800;color:#fff;letter-spacing:-.01em;margin-bottom:5px;}
.hero-card-desc{font-size:12.5px;color:rgba(255,255,255,.6);line-height:1.55;max-width:380px;margin-bottom:14px;}
.hero-card-cta{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:700;color:var(--lime);}
.hero-stats-row{display:flex;gap:14px;margin-bottom:10px;}
.hero-stat{font-size:11px;color:rgba(255,255,255,.5);}
.hero-stat b{color:#fff;font-weight:700;}

/* ── ROSTER CONTROLS ── */
.roster-controls{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;gap:12px;flex-wrap:wrap;}
.roster-title-wrap{display:flex;align-items:center;gap:10px;}
.roster-title{font-size:16px;font-weight:800;color:var(--text);letter-spacing:-.01em;}
.roster-count{background:rgba(61,26,110,.08);color:var(--navy);border-radius:20px;padding:2px 10px;font-size:11px;font-weight:700;}
.roster-actions{display:flex;gap:8px;flex-wrap:wrap;}
.rbtn{display:inline-flex;align-items:center;gap:6px;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 14px;font-size:12.5px;font-weight:600;color:var(--text2);cursor:pointer;transition:all .15s;}
.rbtn:hover{border-color:var(--navy);color:var(--navy);}
.rbtn svg{width:14px;height:14px;}
.rbtn.primary{background:var(--navy);color:#fff;border-color:var(--navy);}
.rbtn.primary:hover{background:var(--navy2);}

.filter-row{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;align-items:center;}
.search-box{flex:1;min-width:180px;position:relative;}
.search-box input{width:100%;border:1px solid var(--border);border-radius:8px;padding:8px 12px 8px 32px;font-size:12.5px;font-family:inherit;outline:none;background:var(--surface);}
.search-box input:focus{border-color:var(--navy);}
.search-box svg{position:absolute;left:10px;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--text3);}
.filter-chip{padding:6px 12px;border-radius:20px;font-size:11.5px;font-weight:600;border:1px solid var(--border);background:var(--surface);color:var(--text2);cursor:pointer;white-space:nowrap;}
.filter-chip.active{background:var(--navy);color:#fff;border-color:var(--navy);}

/* ── STUDENT ROSTER ── */
.roster-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;margin-bottom:24px;}
.student-row{display:grid;grid-template-columns:auto 1fr auto auto auto auto auto auto;align-items:center;gap:14px;padding:13px 18px;border-bottom:.5px solid var(--border);transition:background .15s;}
.student-row:last-child{border-bottom:none;}
.student-row:hover{background:#faf9fd;}
.student-avatar{width:38px;height:38px;border-radius:50%;background:var(--lime-pale);border:2px solid var(--lime);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:var(--lime-dark);flex-shrink:0;}
.student-info{min-width:0;}
.student-name{font-size:13.5px;font-weight:700;color:var(--text);}
.student-meta{font-size:11px;color:var(--text3);margin-top:1px;}
.tag{font-size:10.5px;font-weight:700;padding:3px 9px;border-radius:20px;white-space:nowrap;}
.tag-level-1{background:#fef3c7;color:#92400e;}
.tag-level-2{background:#dbeafe;color:#1e40af;}
.tag-level-3{background:#d4f5e5;color:#2aad62;}
.tag-level-4{background:#ede9fe;color:#5b21b6;}
.tag-level-5{background:#f3f4f6;color:#6b7280;}
.tag-rec{background:rgba(61,26,110,.07);color:var(--navy);}
.tag-type-ind{background:#fee2e2;color:#991b1b;}
.tag-type-grp{background:#e0f2fe;color:#0369a1;}
.student-next{font-size:11px;color:var(--text2);text-align:right;white-space:nowrap;}
.student-next b{display:block;color:var(--text);font-size:12px;font-weight:700;}
.status-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.status-dot.active{background:var(--green);}
.status-dot.pending{background:var(--amber);}

/* ── CALENDAR STRIP ── */
.section-title{font-size:16px;font-weight:800;color:var(--text);letter-spacing:-.01em;margin-bottom:14px;}
.cal-strip{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;}
.cal-day{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 10px;min-height:130px;}
.cal-day.today{border-color:var(--navy);box-shadow:0 0 0 1px var(--navy);}
.cal-day-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text3);margin-bottom:2px;}
.cal-day-num{font-size:16px;font-weight:800;color:var(--text);margin-bottom:8px;}
.cal-day.today .cal-day-num{color:var(--navy);}
.cal-class{background:var(--bg);border-left:3px solid var(--lime);border-radius:6px;padding:5px 7px;margin-bottom:5px;font-size:10px;}
.cal-class-time{font-weight:700;color:var(--navy);font-family:'DM Mono',monospace;font-size:9.5px;}
.cal-class-name{color:var(--text2);margin-top:1px;line-height:1.3;}
.cal-empty{font-size:10px;color:var(--text3);text-align:center;margin-top:20px;}

.toast{position:fixed;top:72px;right:20px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;z-index:999;border-left:3px solid var(--lime);display:none;max-width:300px;line-height:1.5;}
/* ── EVALUATION BUTTON ── */
.eval-btn{font-size:11px;font-weight:600;padding:6px 12px;border-radius:7px;cursor:pointer;white-space:nowrap;border:1px solid transparent;transition:all .15s;}
.eval-btn.see{background:var(--navy);color:#fff;border-color:var(--navy);}
.eval-btn.see:hover{background:var(--navy2);}
.eval-btn.do{background:#fff7ed;color:var(--amber);border:1.5px dashed #fcd34d;}
.eval-btn.do:hover{background:#fef3c7;border-color:var(--amber);}

/* ── MODAL OVERLAY ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(26,10,46,.5);backdrop-filter:blur(3px);z-index:1000;align-items:center;justify-content:center;padding:24px;}
.modal-overlay.open{display:flex;}
.modal-box{background:var(--surface);border-radius:16px;max-width:680px;width:100%;max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(61,26,110,.3);}
.modal-header{position:sticky;top:0;background:var(--navy);color:#fff;padding:18px 24px;border-radius:16px 16px 0 0;display:flex;align-items:center;justify-content:space-between;z-index:5;}
.modal-header-l{display:flex;align-items:center;gap:12px;}
.modal-avatar{width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,.12);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;flex-shrink:0;}
.modal-title{font-size:15px;font-weight:700;color:#fff;}
.modal-sub{font-size:11px;color:rgba(255,255,255,.55);margin-top:2px;}
.modal-close{cursor:pointer;color:rgba(255,255,255,.55);font-size:20px;line-height:1;background:none;border:none;padding:4px;}
.modal-close:hover{color:#fff;}
.modal-body{padding:22px 24px;}

/* ── EVAL VIEW (read-only, Fernando demo) ── */
.eval-score-hero{display:flex;gap:14px;margin-bottom:20px;}
.eval-score-card{flex:1;background:var(--bg);border-radius:12px;padding:16px;text-align:center;}
.eval-score-num{font-size:28px;font-weight:800;font-family:'DM Mono',monospace;}
.eval-score-label{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;margin-top:4px;font-weight:600;}
.eval-section-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--text2);margin:20px 0 10px;}
.eval-section-title:first-child{margin-top:0;}
.eval-metric{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:.5px solid var(--border);}
.eval-metric:last-child{border-bottom:none;}
.eval-metric-name{font-size:13px;color:var(--text);}
.eval-stars{display:flex;gap:3px;}
.eval-star{width:14px;height:14px;}
.eval-notes{background:var(--bg);border-left:3px solid var(--lime);border-radius:8px;padding:14px 16px;font-size:13px;color:var(--text2);line-height:1.65;}
.eval-trend{display:flex;gap:8px;align-items:flex-end;height:50px;margin-top:8px;}
.eval-trend-bar{flex:1;background:rgba(61,26,110,.12);border-radius:4px 4px 0 0;position:relative;display:flex;align-items:flex-end;justify-content:center;}
.eval-trend-bar.current{background:var(--navy);}
.eval-trend-label{position:absolute;bottom:-18px;font-size:9px;color:var(--text3);white-space:nowrap;}
.eval-trend-val{position:absolute;top:-16px;font-size:10px;font-weight:700;color:var(--text2);}
.eval-trend-bar.current .eval-trend-val{color:var(--navy);}

/* ── EVAL FORM (Do evaluation, empty) ── */
.form-group{margin-bottom:16px;}
.form-label{font-size:12px;font-weight:600;color:var(--text);margin-bottom:8px;display:block;}
.form-rating{display:flex;gap:6px;}
.form-rating-btn{width:36px;height:36px;border-radius:8px;border:1px solid var(--border);background:var(--surface);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:var(--text3);cursor:pointer;transition:all .15s;}
.form-rating-btn:hover{border-color:var(--navy);color:var(--navy);}
.form-rating-btn.selected{background:var(--navy);border-color:var(--navy);color:#fff;}
.form-textarea{width:100%;min-height:90px;border:1px solid var(--border);border-radius:8px;padding:10px 12px;font-size:13px;font-family:inherit;color:var(--text);resize:vertical;outline:none;}
.form-textarea:focus{border-color:var(--navy);}
.form-submit{width:100%;background:var(--navy);color:#fff;font-size:13px;font-weight:700;padding:12px;border-radius:9px;border:none;cursor:pointer;margin-top:8px;}
.form-submit:hover{background:var(--navy2);}

.at-nbtn{font-size:11px;font-weight:600;padding:6px 12px;border-radius:7px;cursor:pointer;white-space:nowrap;border:1px solid transparent;transition:all .15s;background:rgba(61,26,110,.06);color:var(--navy);border-color:rgba(61,26,110,.15);}
.at-nbtn:hover{background:rgba(61,26,110,.12);}

.at-overlay{display:none;position:fixed;inset:0;background:rgba(5,8,15,.6);backdrop-filter:blur(4px);z-index:1001;align-items:center;justify-content:center;padding:20px;}
.at-overlay.open{display:flex;}
.at-box{background:#0a1020;border:1px solid rgba(255,255,255,.08);border-radius:16px;max-width:480px;width:100%;max-height:86vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.5);}
.at-header{position:sticky;top:0;background:#3d1a6e;padding:18px 22px;border-radius:16px 16px 0 0;display:flex;align-items:center;justify-content:space-between;z-index:5;}
.at-htitle{font-size:14px;font-weight:700;color:#fff;}
.at-hsub{font-size:11px;color:rgba(255,255,255,.55);margin-top:3px;}
.at-close{cursor:pointer;color:rgba(255,255,255,.55);font-size:20px;line-height:1;background:none;border:none;padding:4px;}
.at-close:hover{color:#fff;}
.at-body{padding:20px 22px;}

.at-student{display:flex;align-items:center;gap:11px;background:rgba(255,255,255,.04);border-radius:10px;padding:11px 13px;margin-bottom:16px;}
.at-student-avatar{width:34px;height:34px;border-radius:50%;background:#d4f5e5;color:#2aad62;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0;}
.at-student-name{font-size:12.5px;font-weight:700;color:#fff;}
.at-student-sub{font-size:10.5px;color:rgba(255,255,255,.45);margin-top:1px;}

.at-search{width:100%;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:9px 12px;font-size:13px;font-family:inherit;color:#fff;outline:none;margin-bottom:12px;}
.at-search::placeholder{color:rgba(255,255,255,.25);}
.at-search:focus{border-color:#3ecf7e;}

.at-tab-row{display:flex;gap:6px;margin-bottom:12px;}
.at-tab{padding:6px 13px;border-radius:20px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid rgba(255,255,255,.1);color:rgba(255,255,255,.4);}
.at-tab.sel{background:#3d1a6e;color:#fff;border-color:#7c4de0;}

.at-list{display:flex;flex-direction:column;gap:6px;margin-bottom:16px;max-height:260px;overflow-y:auto;}
.at-item{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:9px;padding:9px 11px;cursor:pointer;transition:all .15s;}
.at-item:hover{border-color:rgba(255,255,255,.2);}
.at-item.sel{border-color:#3ecf7e;background:rgba(62,207,126,.08);}
.at-icon{width:26px;height:26px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;}
.at-icon.priv{background:rgba(124,77,224,.2);color:#a78bfa;}
.at-icon.lib{background:rgba(62,207,126,.15);color:#3ecf7e;}
.at-text{flex:1;min-width:0;}
.at-name{font-size:11.5px;font-weight:700;color:#fff;}
.at-meta{font-size:9.5px;color:rgba(255,255,255,.4);margin-top:1px;}
.at-check{width:18px;height:18px;border-radius:50%;border:1.5px solid rgba(255,255,255,.2);flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:10px;color:transparent;}
.at-item.sel .at-check{background:#3ecf7e;border-color:#3ecf7e;color:#0a2a16;}

.at-empty{text-align:center;padding:24px 10px;font-size:12px;color:rgba(255,255,255,.3);}

.at-submit{width:100%;background:#3ecf7e;color:#0a2a16;font-size:13px;font-weight:700;padding:12px;border-radius:9px;border:none;cursor:pointer;transition:background .15s;}
.at-submit:hover{background:#34b86c;}

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
      <div class="logo-sub">Padel Coach Hub</div>
    </div>
  </div>
  <div class="header-right">
    <div class="coach-chip"><div class="dot"></div>Coach Toni Alcala</div>
    <button class="btn-logout" onclick="window.location.href='/'">Sign out</button>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="main">

  <div class="welcome">
    <div class="welcome-title">Good morning, Toni 🎾</div>
    <div class="welcome-sub">Padel Lab Madrid &middot; 10 students enrolled &middot; Orbis Core active</div>
  </div>

  <!-- HERO: Tactical Simulator + Video Analysis -->
  <div class="hero-row">

    <div class="hero-card simulator" onclick="window.location.href='/demo/simulator'">
      <div class="hero-badge-new">+300 plays library</div>
      <div class="hero-icon-wrap">
        <svg viewBox="0 0 24 24" fill="none" stroke="#3ecf7e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
      </div>
      <div class="hero-card-title">Tactical Simulator</div>
      <div class="hero-card-desc">Animated padel plays grounded in FIP Academy &mdash; show students exactly how a point should unfold, from beginner to advanced.</div>
      <div class="hero-stats-row">
        <div class="hero-stat"><b>18</b> demo plays</div>
        <div class="hero-stat"><b>3</b> levels</div>
      </div>
      <div class="hero-card-cta">Open simulator &rarr;</div>
    </div>

    <div class="hero-card video" onclick="window.location.href='/demo/video'">
      <div class="hero-badge-new">Orbis Core analyzed</div>
      <div class="hero-icon-wrap">
        <svg viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
      </div>
      <div class="hero-card-title">Video Analysis</div>
      <div class="hero-card-desc">Upload a session clip &mdash; Orbis Core breaks down technique frame by frame with FIP drill recommendations per finding.</div>
      <div class="hero-stats-row">
        <div class="hero-stat"><b>3.5/5</b> last score</div>
        <div class="hero-stat"><b>6</b> findings</div>
      </div>
      <div class="hero-card-cta">Open video analysis &rarr;</div>
    </div>

  </div>

  <!-- ROSTER CONTROLS -->
  <div class="roster-controls">
    <div class="roster-title-wrap">
      <div class="roster-title">My students</div>
      <div class="roster-count">10</div>
    </div>
    <div class="roster-actions">
      <button class="rbtn" onclick="showToast('Template downloaded — fill in and re-upload to bulk update your roster')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Download template
      </button>
      <button class="rbtn primary" onclick="showToast('Excel upload — drag a .xlsx file here to bulk update your roster')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        Upload Excel
      </button>
      <button class="rbtn" onclick="showToast('Invitation form coming up')">+ Invite student</button>
    </div>
  </div>

  <div class="filter-row">
    <div class="search-box">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" placeholder="Search students...">
    </div>
    <div class="filter-chip active">All levels</div>
    <div class="filter-chip">1ª &mdash; Pro</div>
    <div class="filter-chip">2ª</div>
    <div class="filter-chip">3ª</div>
    <div class="filter-chip">4ª</div>
    <div class="filter-chip">5ª &mdash; Amateur</div>
  </div>

  <!-- STUDENT ROSTER -->
  <div class="roster-card">

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">F</div>
        <div class="student-info">
          <div class="student-name">Fernando de los Rios</div>
          <div class="student-meta">Joined Jun 2026 &middot; 7 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-3">3ª categoria</span>
      <span class="tag tag-rec">2x / week</span>
      <span class="tag tag-type-ind">Individual</span>
      <div class="student-next">Next class<b>Thu 26, 10:00</b></div>
      <div class="eval-btn see" onclick="openModal('evalSeeModal')">See evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Fernando de los Rios','F','Thu 26, 10:00')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">J</div>
        <div class="student-info">
          <div class="student-name">James Whitfield</div>
          <div class="student-meta">Joined Jun 2026 &middot; 5 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-4">4ª categoria</span>
      <span class="tag tag-rec">1x / week</span>
      <span class="tag tag-type-grp">Group</span>
      <div class="student-next">Next class<b>Fri 27, 18:00</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('james')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('James Whitfield','J','Fri 27, 18:00')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot pending"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">J</div>
        <div class="student-info">
          <div class="student-name">Jaime Robles</div>
          <div class="student-meta">Invited Jun 2026 &middot; Pending acceptance</div>
        </div>
      </div>
      <span class="tag tag-level-2">2ª categoria</span>
      <span class="tag tag-rec">+2x / week</span>
      <span class="tag tag-type-ind">Individual</span>
      <div class="student-next">Next class<b>&mdash;</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('jaime')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Jaime Robles','J','TBD')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">M</div>
        <div class="student-info">
          <div class="student-name">Marta Iglesias</div>
          <div class="student-meta">Joined May 2026 &middot; 14 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-1">1ª &mdash; Pro</span>
      <span class="tag tag-rec">+2x / week</span>
      <span class="tag tag-type-ind">Individual</span>
      <div class="student-next">Next class<b>Wed 25, 09:00</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('marta')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Marta Iglesias','M','Wed 25, 09:00')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">D</div>
        <div class="student-info">
          <div class="student-name">Diego Fernandez</div>
          <div class="student-meta">Joined Apr 2026 &middot; 22 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-2">2ª categoria</span>
      <span class="tag tag-rec">2x / week</span>
      <span class="tag tag-type-grp">Group</span>
      <div class="student-next">Next class<b>Thu 26, 19:00</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('diego')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Diego Fernandez','D','Thu 26, 19:00')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">L</div>
        <div class="student-info">
          <div class="student-name">Lucia Moreno</div>
          <div class="student-meta">Joined Jun 2026 &middot; 3 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-5">5ª &mdash; Amateur</span>
      <span class="tag tag-rec">&lt;1x / week</span>
      <span class="tag tag-type-grp">Group</span>
      <div class="student-next">Next class<b>Sat 28, 11:00</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('lucia')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Lucia Moreno','L','Sat 28, 11:00')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">P</div>
        <div class="student-info">
          <div class="student-name">Pablo Santos</div>
          <div class="student-meta">Joined Mar 2026 &middot; 31 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-1">1ª &mdash; Pro</span>
      <span class="tag tag-rec">+2x / week</span>
      <span class="tag tag-type-ind">Individual</span>
      <div class="student-next">Next class<b>Wed 25, 17:00</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('pablo')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Pablo Santos','P','Wed 25, 17:00')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">C</div>
        <div class="student-info">
          <div class="student-name">Carla Navarro</div>
          <div class="student-meta">Joined May 2026 &middot; 9 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-3">3ª categoria</span>
      <span class="tag tag-rec">1x / week</span>
      <span class="tag tag-type-grp">Group</span>
      <div class="student-next">Next class<b>Fri 27, 09:00</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('carla')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Carla Navarro','C','Fri 27, 09:00')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">A</div>
        <div class="student-info">
          <div class="student-name">Alvaro Gimenez</div>
          <div class="student-meta">Joined Feb 2026 &middot; 38 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-2">2ª categoria</span>
      <span class="tag tag-rec">2x / week</span>
      <span class="tag tag-type-ind">Individual</span>
      <div class="student-next">Next class<b>Thu 26, 08:00</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('alvaro')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Alvaro Gimenez','A','Thu 26, 08:00')">Assign tactic</div>
    </div>

    <div class="student-row">
      <div class="status-dot active"></div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div class="student-avatar">S</div>
        <div class="student-info">
          <div class="student-name">Sofia Castellanos</div>
          <div class="student-meta">Joined Jun 2026 &middot; 4 sessions logged</div>
        </div>
      </div>
      <span class="tag tag-level-4">4ª categoria</span>
      <span class="tag tag-rec">&lt;1x / week</span>
      <span class="tag tag-type-ind">Individual</span>
      <div class="student-next">Next class<b>Sat 28, 16:00</b></div>
      <div class="eval-btn do" onclick="openDoEvaluation('sofia')">Do evaluation</div>
      <div class="at-nbtn" onclick="openAssignTactic('Sofia Castellanos','S','Sat 28, 16:00')">Assign tactic</div>
    </div>

  </div>

  <!-- WEEKLY CALENDAR -->
  <div class="section-title">This week's classes</div>
  <div class="cal-strip">

    <div class="cal-day">
      <div class="cal-day-label">Mon</div>
      <div class="cal-day-num">23</div>
      <div class="cal-empty">No classes</div>
    </div>

    <div class="cal-day">
      <div class="cal-day-label">Tue</div>
      <div class="cal-day-num">24</div>
      <div class="cal-empty">No classes</div>
    </div>

    <div class="cal-day today">
      <div class="cal-day-label">Wed</div>
      <div class="cal-day-num">25</div>
      <div class="cal-class"><div class="cal-class-time">09:00</div><div class="cal-class-name">Marta Iglesias</div></div>
      <div class="cal-class"><div class="cal-class-time">17:00</div><div class="cal-class-name">Pablo Santos</div></div>
    </div>

    <div class="cal-day">
      <div class="cal-day-label">Thu</div>
      <div class="cal-day-num">26</div>
      <div class="cal-class"><div class="cal-class-time">08:00</div><div class="cal-class-name">Alvaro Gimenez</div></div>
      <div class="cal-class"><div class="cal-class-time">10:00</div><div class="cal-class-name">Fernando de los Rios</div></div>
      <div class="cal-class"><div class="cal-class-time">19:00</div><div class="cal-class-name">Diego Fernandez (group)</div></div>
    </div>

    <div class="cal-day">
      <div class="cal-day-label">Fri</div>
      <div class="cal-day-num">27</div>
      <div class="cal-class"><div class="cal-class-time">09:00</div><div class="cal-class-name">Carla Navarro (group)</div></div>
      <div class="cal-class"><div class="cal-class-time">18:00</div><div class="cal-class-name">James Whitfield (group)</div></div>
    </div>

    <div class="cal-day">
      <div class="cal-day-label">Sat</div>
      <div class="cal-day-num">28</div>
      <div class="cal-class"><div class="cal-class-time">11:00</div><div class="cal-class-name">Lucia Moreno (group)</div></div>
      <div class="cal-class"><div class="cal-class-time">16:00</div><div class="cal-class-name">Sofia Castellanos</div></div>
    </div>

    <div class="cal-day">
      <div class="cal-day-label">Sun</div>
      <div class="cal-day-num">29</div>
      <div class="cal-empty">No classes</div>
    </div>

  </div>

</div>

<script>
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3500);
}

document.querySelectorAll('.filter-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
  });
});
function openModal(id){document.getElementById(id).classList.add('open');}
function closeModal(id){document.getElementById(id).classList.remove('open');}

const studentInitials={marta:'M',pablo:'P',diego:'D',lucia:'L',carla:'C',alvaro:'A',sofia:'S',jaime:'J',james:'J'};
const studentNames={marta:'Marta Iglesias',pablo:'Pablo Santos',diego:'Diego Fernandez',lucia:'Lucia Moreno',carla:'Carla Navarro',alvaro:'Alvaro Gimenez',sofia:'Sofia Castellanos',jaime:'Jaime Robles',james:'James Whitfield'};

function openDoEvaluation(studentKey){
  document.getElementById('doEvalAvatar').textContent=studentInitials[studentKey]||'?';
  document.getElementById('doEvalTitle').textContent=(studentNames[studentKey]||'Student')+' — New evaluation';
  document.getElementById('doEvalSub').textContent='Session: today · build a record for this class';
  resetEvalForm();
  openModal('evalDoModal');
}

document.addEventListener('click',function(e){
  if(e.target.classList.contains('form-rating-btn')){
    const group=e.target.parentElement;
    group.querySelectorAll('.form-rating-btn').forEach(b=>b.classList.remove('selected'));
    e.target.classList.add('selected');
    const val=parseInt(e.target.dataset.val);
    let cur=val;
    [...group.children].forEach(b=>{
      if(parseInt(b.dataset.val)<=val)b.classList.add('selected');
      else b.classList.remove('selected');
    });
  }
});

function resetEvalForm(){
  document.querySelectorAll('#evalDoModal .form-rating-btn').forEach(b=>b.classList.remove('selected'));
  document.querySelector('#evalDoModal .form-textarea').value='';
}

function submitEvaluation(){
  closeModal('evalDoModal');
  showToast('Evaluation saved — student record updated');
}

let atSelectedItem=null;
let atCurrentStudent={name:'',avatar:'',session:''};

function openAssignTactic(studentName,avatar,session){
  atCurrentStudent={name:studentName,avatar:avatar,session:session};
  document.getElementById('atStudentName').textContent=studentName;
  document.getElementById('atAvatar').textContent=avatar;
  document.getElementById('atSessionInfo').textContent='Next session: '+session;
  resetAtForm();
  document.getElementById('assignTacticModal').classList.add('open');
}

function closeAssignTactic(){
  document.getElementById('assignTacticModal').classList.remove('open');
}

function resetAtForm(){
  document.getElementById('atSearch').value='';
  document.querySelectorAll('.at-item').forEach(i=>i.classList.remove('sel'));
  document.querySelectorAll('.at-tab').forEach(t=>t.classList.remove('sel'));
  document.querySelector('.at-tab[data-tab="all"]').classList.add('sel');
  atSelectedItem=null;
  filterAtList();
}

function selectAtItem(el){
  document.querySelectorAll('.at-item').forEach(i=>i.classList.remove('sel'));
  el.classList.add('sel');
  atSelectedItem=el.dataset.name;
}

function selectAtTab(el){
  document.querySelectorAll('.at-tab').forEach(t=>t.classList.remove('sel'));
  el.classList.add('sel');
  filterAtList();
}

function filterAtList(){
  const query=document.getElementById('atSearch').value.trim().toLowerCase();
  const activeTab=document.querySelector('.at-tab.sel').dataset.tab;
  const items=document.querySelectorAll('.at-item');
  let visibleCount=0;
  items.forEach(item=>{
    const matchesQuery=!query||item.dataset.name.includes(query);
    const matchesTab=activeTab==='all'||item.dataset.source===activeTab;
    const show=matchesQuery&&matchesTab;
    item.style.display=show?'flex':'none';
    if(show)visibleCount++;
  });
}

function submitAssignTactic(){
  if(!atSelectedItem){
    showToast('Pick a tactic to assign');
    return;
  }
  closeAssignTactic();
  showToast('Tactic assigned to '+atCurrentStudent.name+'\u2019s next session');
}

</script>
<div class="modal-overlay" id="evalSeeModal">
  <div class="modal-box">
    <div class="modal-header">
      <div class="modal-header-l">
        <div class="modal-avatar">F</div>
        <div>
          <div class="modal-title">Fernando de los Rios — Evaluation</div>
          <div class="modal-sub">Session: Thu Jun 26, 2026 &middot; 10:00 &middot; Individual class</div>
        </div>
      </div>
      <button class="modal-close" onclick="closeModal('evalSeeModal')">&#10005;</button>
    </div>
    <div class="modal-body">

      <div class="eval-score-hero">
        <div class="eval-score-card">
          <div class="eval-score-num" style="color:var(--lime-dark);">3.6</div>
          <div class="eval-score-label">Technical</div>
        </div>
        <div class="eval-score-card">
          <div class="eval-score-num" style="color:var(--navy);">3.3</div>
          <div class="eval-score-label">Tactical</div>
        </div>
        <div class="eval-score-card">
          <div class="eval-score-num" style="color:var(--amber);">3.5</div>
          <div class="eval-score-label">Overall</div>
        </div>
      </div>

      <div class="eval-section-title">Technical</div>
      <div class="eval-metric">
        <span class="eval-metric-name">Paddle control</span>
        <span style="color:var(--lime-dark);font-weight:700;font-size:13px;">&#9733;&#9733;&#9733;&#9733;&#9734;</span>
      </div>
      <div class="eval-metric">
        <span class="eval-metric-name">Shot consistency</span>
        <span style="color:var(--lime-dark);font-weight:700;font-size:13px;">&#9733;&#9733;&#9733;&#9734;&#9734;</span>
      </div>
      <div class="eval-metric">
        <span class="eval-metric-name">Court coverage / footwork</span>
        <span style="color:var(--lime-dark);font-weight:700;font-size:13px;">&#9733;&#9733;&#9733;&#9733;&#9734;</span>
      </div>

      <div class="eval-section-title">Tactical</div>
      <div class="eval-metric">
        <span class="eval-metric-name">Shot selection</span>
        <span style="color:var(--navy);font-weight:700;font-size:13px;">&#9733;&#9733;&#9733;&#9734;&#9734;</span>
      </div>
      <div class="eval-metric">
        <span class="eval-metric-name">Court positioning</span>
        <span style="color:var(--navy);font-weight:700;font-size:13px;">&#9733;&#9733;&#9733;&#9733;&#9734;</span>
      </div>
      <div class="eval-metric">
        <span class="eval-metric-name">Point construction</span>
        <span style="color:var(--navy);font-weight:700;font-size:13px;">&#9733;&#9733;&#9733;&#9734;&#9734;</span>
      </div>

      <div class="eval-section-title">Progress &mdash; last 4 sessions</div>
      <div class="eval-trend">
        <div class="eval-trend-bar" style="height:55%;">
          <div class="eval-trend-val">3.1</div>
          <div class="eval-trend-label">May 29</div>
        </div>
        <div class="eval-trend-bar" style="height:62%;">
          <div class="eval-trend-val">3.2</div>
          <div class="eval-trend-label">Jun 5</div>
        </div>
        <div class="eval-trend-bar" style="height:70%;">
          <div class="eval-trend-val">3.4</div>
          <div class="eval-trend-label">Jun 12</div>
        </div>
        <div class="eval-trend-bar current" style="height:78%;">
          <div class="eval-trend-val">3.5</div>
          <div class="eval-trend-label">Jun 26</div>
        </div>
      </div>

      <div class="eval-section-title">Coach notes</div>
      <div class="eval-notes">Good improvement on net positioning today &mdash; he's holding the volley zone better instead of drifting back. Still rushing the bandeja under pressure, leading to a few unforced errors in the second half. Worth revisiting the wall-bounce contact-point drill next session. Confidence is up since switching partners with James.</div>

    </div>
  </div>
</div>

<div class="modal-overlay" id="evalDoModal">
  <div class="modal-box">
    <div class="modal-header">
      <div class="modal-header-l">
        <div class="modal-avatar" id="doEvalAvatar">M</div>
        <div>
          <div class="modal-title" id="doEvalTitle">Marta Iglesias — New evaluation</div>
          <div class="modal-sub" id="doEvalSub">Session: today &middot; build a record for this class</div>
        </div>
      </div>
      <button class="modal-close" onclick="closeModal('evalDoModal')">&#10005;</button>
    </div>
    <div class="modal-body">

      <div class="eval-section-title" style="margin-top:0;">Technical</div>

      <div class="form-group">
        <label class="form-label">Paddle control</label>
        <div class="form-rating" data-field="paddle">
          <div class="form-rating-btn" data-val="1">1</div>
          <div class="form-rating-btn" data-val="2">2</div>
          <div class="form-rating-btn" data-val="3">3</div>
          <div class="form-rating-btn" data-val="4">4</div>
          <div class="form-rating-btn" data-val="5">5</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Shot consistency</label>
        <div class="form-rating" data-field="consistency">
          <div class="form-rating-btn" data-val="1">1</div>
          <div class="form-rating-btn" data-val="2">2</div>
          <div class="form-rating-btn" data-val="3">3</div>
          <div class="form-rating-btn" data-val="4">4</div>
          <div class="form-rating-btn" data-val="5">5</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Court coverage / footwork</label>
        <div class="form-rating" data-field="footwork">
          <div class="form-rating-btn" data-val="1">1</div>
          <div class="form-rating-btn" data-val="2">2</div>
          <div class="form-rating-btn" data-val="3">3</div>
          <div class="form-rating-btn" data-val="4">4</div>
          <div class="form-rating-btn" data-val="5">5</div>
        </div>
      </div>

      <div class="eval-section-title">Tactical</div>

      <div class="form-group">
        <label class="form-label">Shot selection</label>
        <div class="form-rating" data-field="selection">
          <div class="form-rating-btn" data-val="1">1</div>
          <div class="form-rating-btn" data-val="2">2</div>
          <div class="form-rating-btn" data-val="3">3</div>
          <div class="form-rating-btn" data-val="4">4</div>
          <div class="form-rating-btn" data-val="5">5</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Court positioning</label>
        <div class="form-rating" data-field="positioning">
          <div class="form-rating-btn" data-val="1">1</div>
          <div class="form-rating-btn" data-val="2">2</div>
          <div class="form-rating-btn" data-val="3">3</div>
          <div class="form-rating-btn" data-val="4">4</div>
          <div class="form-rating-btn" data-val="5">5</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Point construction</label>
        <div class="form-rating" data-field="construction">
          <div class="form-rating-btn" data-val="1">1</div>
          <div class="form-rating-btn" data-val="2">2</div>
          <div class="form-rating-btn" data-val="3">3</div>
          <div class="form-rating-btn" data-val="4">4</div>
          <div class="form-rating-btn" data-val="5">5</div>
        </div>
      </div>

      <div class="eval-section-title">Coach notes</div>
      <div class="form-group">
        <textarea class="form-textarea" placeholder="What did you notice this session? Technique fixes, tactical patterns, energy and confidence, drills to revisit next time..."></textarea>
      </div>

      <button class="form-submit" onclick="submitEvaluation()">Save evaluation</button>

    </div>
  </div>
</div>

<div class="at-overlay" id="assignTacticModal">
  <div class="at-box">
    <div class="at-header">
      <div>
        <div class="at-htitle">Assign a tactic</div>
        <div class="at-hsub">Choose from your library and link it to this session</div>
      </div>
      <button class="at-close" onclick="closeAssignTactic()">&#10005;</button>
    </div>
    <div class="at-body">

      <div class="at-student">
        <div class="at-student-avatar" id="atAvatar">F</div>
        <div>
          <div class="at-student-name" id="atStudentName">Fernando de los Rios</div>
          <div class="at-student-sub" id="atSessionInfo">Next session: Thu 26, 10:00</div>
        </div>
      </div>

      <input class="at-search" placeholder="Search tactics..." id="atSearch" oninput="filterAtList()">

      <div class="at-tab-row">
        <div class="at-tab sel" data-tab="all" onclick="selectAtTab(this)">All</div>
        <div class="at-tab" data-tab="private" onclick="selectAtTab(this)">My private</div>
        <div class="at-tab" data-tab="library" onclick="selectAtTab(this)">+300 library</div>
      </div>

      <div class="at-list" id="atList">
        <div class="at-item" data-source="private" data-name="my fake bandeja drill" onclick="selectAtItem(this)">
          <div class="at-icon priv">&#128274;</div>
          <div class="at-text">
            <div class="at-name">My fake bandeja drill</div>
            <div class="at-meta">Private &middot; created by you</div>
          </div>
          <div class="at-check">&#10003;</div>
        </div>
        <div class="at-item" data-source="library" data-name="bandeja hold at net" onclick="selectAtItem(this)">
          <div class="at-icon lib">&#127934;</div>
          <div class="at-text">
            <div class="at-name">Bandeja hold at net</div>
            <div class="at-meta">+300 library &middot; Intermediate</div>
          </div>
          <div class="at-check">&#10003;</div>
        </div>
        <div class="at-item" data-source="library" data-name="serve plus net rush" onclick="selectAtItem(this)">
          <div class="at-icon lib">&#127934;</div>
          <div class="at-text">
            <div class="at-name">Serve + net rush</div>
            <div class="at-meta">+300 library &middot; Beginner</div>
          </div>
          <div class="at-check">&#10003;</div>
        </div>
        <div class="at-item" data-source="library" data-name="vibora to side glass" onclick="selectAtItem(this)">
          <div class="at-icon lib">&#127934;</div>
          <div class="at-text">
            <div class="at-name">Vibora to side glass</div>
            <div class="at-meta">+300 library &middot; Advanced</div>
          </div>
          <div class="at-check">&#10003;</div>
        </div>
      </div>

      <button class="at-submit" onclick="submitAssignTactic()">Assign to this session</button>

    </div>
  </div>
</div>

</body>
</html>"""
SIMULATOR_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>Orbis AI — Padel Tactical Simulator</title>\n<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">\n<style>\n*{box-sizing:border-box;margin:0;padding:0;}\nhtml,body{height:100%;background:#f2f0f7;font-family:\'Inter\',system-ui,sans-serif;color:#1a0a2e;overflow:hidden;}\n.app{height:100vh;display:flex;flex-direction:column;background:#f2f0f7;}\n\n/* NAV */\n.nav{height:56px;background:#3d1a6e;border-bottom:1px solid rgba(255,255,255,.08);display:flex;align-items:center;justify-content:space-between;padding:0 20px;flex-shrink:0;box-shadow:0 2px 12px rgba(61,26,110,.2);}\n.nav-l{display:flex;align-items:center;gap:10px;}\n.logo{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:700;color:#fff;letter-spacing:-.02em;}\n.logo em{color:#3ecf7e;font-style:normal;}\n.ndiv{width:1px;height:16px;background:rgba(255,255,255,.18);}\n.nsub{font-size:11px;color:rgba(255,255,255,.55);font-weight:500;}\n.nav-r{display:flex;align-items:center;gap:8px;}\n.npill{background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:4px 11px;font-size:10.5px;font-weight:700;color:#3ecf7e;}\n.nbtn{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:8px;padding:6px 12px;font-size:10.5px;font-weight:600;color:rgba(255,255,255,.85);cursor:pointer;transition:background .15s;}\n.nbtn:hover{background:rgba(255,255,255,.18);}\n\n/* LEVEL BAR */\n.lbar{height:46px;background:#fff;border-bottom:1px solid #e2e6ef;display:flex;align-items:center;gap:6px;padding:0 20px;flex-shrink:0;}\n.lv{padding:5px 15px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;color:#9a8aaa;border:1px solid transparent;transition:all .2s;}\n.lv.lg{background:#d4f5e5;border-color:#9be8c4;color:#2aad62;}\n.lv.li{background:#fef3c7;border-color:#fcd989;color:#b45309;}\n.lv.lr{background:#fee2e2;border-color:#fca5a5;color:#b91c1c;}\n.lsep{flex:1;}\n.lcnt{font-size:11px;color:#9a8aaa;font-weight:600;}\n\n/* PLAY CHIPS */\n.pbar{background:#f2f0f7;border-bottom:1px solid #e2e6ef;padding:10px 20px;display:flex;gap:7px;overflow-x:auto;flex-shrink:0;scrollbar-width:none;}\n.pbar::-webkit-scrollbar{display:none;}\n.pc{padding:6px 14px;border-radius:8px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid #e2e6ef;background:#fff;color:#5a4a7a;white-space:nowrap;flex-shrink:0;transition:all .2s;}\n.pc:hover{border-color:#3d1a6e;}\n.pc.pca{background:#3d1a6e;border-color:#3d1a6e;color:#fff;}\n\n/* BODY */\n.body{display:grid;grid-template-columns:1fr 240px;flex:1;min-height:0;overflow:hidden;}\n\n/* COURT PANEL */\n.cpanel{background:#e8e4f0;display:flex;flex-direction:column;position:relative;overflow:hidden;}\n.cglow{position:absolute;inset:0;background:radial-gradient(ellipse 60% 40% at 50% 52%,rgba(61,26,110,.04) 0%,transparent 65%);pointer-events:none;}\n.cwrap{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;padding:18px 20px 6px;position:relative;}\n#court{display:block;max-width:100%;max-height:100%;}\n\n/* SHOT BAR */\n.shotbar{padding:9px 18px;display:flex;align-items:center;gap:9px;background:#fff;border-top:1px solid #e2e6ef;flex-shrink:0;}\n.sdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}\n.stxt{font-size:12.5px;font-weight:600;color:#3d2a5e;flex:1;}\n.sbadge{font-size:9.5px;font-weight:700;padding:3px 9px;border-radius:20px;}\n\n/* CONTROLS */\n.ctrl{background:#fff;border-top:1px solid #e2e6ef;padding:11px 20px;display:flex;align-items:center;gap:10px;flex-shrink:0;}\n.playbtn{width:38px;height:38px;border-radius:50%;background:#3ecf7e;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:transform .15s;box-shadow:0 2px 8px rgba(62,207,126,.35);}\n.playbtn:active{transform:scale(.92);}\n.playbtn svg{width:13px;height:13px;fill:#0a2a16;}\n.playbtn.playing svg{margin-left:0;}\n.ptrack{flex:1;height:4px;background:#e2e6ef;border-radius:3px;position:relative;cursor:pointer;}\n.pfill{height:100%;background:linear-gradient(90deg,#3ecf7e,#2aad62);border-radius:3px;width:0%;transition:none;}\n.pthumb{width:12px;height:12px;border-radius:50%;background:#3ecf7e;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.2);position:absolute;top:-4px;left:-6px;transition:none;}\n.pmeta{font-size:11px;color:#9a8aaa;font-weight:600;white-space:nowrap;}\n.cbtns{display:flex;gap:6px;}\n.cbtn{background:#f2f0f7;border:1px solid #e2e6ef;border-radius:7px;padding:6px 12px;font-size:11px;font-weight:600;color:#5a4a7a;cursor:pointer;transition:all .15s;}\n.cbtn:hover{background:#e8e4f0;color:#3d1a6e;}\n.cbtn.cg{background:#d4f5e5;border-color:#9be8c4;color:#2aad62;}\n\n/* RIGHT PANEL */\n.rp{background:#fff;border-left:1px solid #e2e6ef;display:flex;flex-direction:column;overflow:hidden;}\n.rps{padding:15px 16px;border-bottom:1px solid #e2e6ef;flex-shrink:0;}\n.rpl{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#9a8aaa;margin-bottom:7px;}\n.rpname{font-size:14px;font-weight:800;color:#1a0a2e;letter-spacing:-.01em;line-height:1.2;margin-bottom:6px;}\n.rptags{display:flex;gap:5px;margin-bottom:9px;flex-wrap:wrap;}\n.rptag{padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700;}\n.rpdesc{font-size:11px;color:#5a4a7a;line-height:1.65;}\n.rpseq{padding:11px 16px;flex:1;overflow-y:auto;scrollbar-width:none;}\n.rpseq::-webkit-scrollbar{display:none;}\n.seqi{display:flex;align-items:flex-start;gap:8px;padding:6px 7px;border-radius:7px;margin-bottom:2px;cursor:pointer;transition:background .15s;}\n.seqi.sa{background:#f0ebfa;}\n.seqn{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:9.5px;font-weight:700;flex-shrink:0;margin-top:1px;}\n.seqt{font-size:11px;color:#9a8aaa;line-height:1.45;padding-top:1px;}\n.seqi.sa .seqt{color:#3d1a6e;font-weight:600;}\n.seqw{font-size:9.5px;color:#d97706;font-weight:700;margin-top:1px;}\n.seqe{font-size:9.5px;color:#dc2626;font-weight:700;margin-top:1px;}\n.fip{padding:13px 16px;background:#f7f5fb;border-top:1px solid #e2e6ef;flex-shrink:0;}\n.fipl{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#7c4de0;margin-bottom:5px;display:flex;align-items:center;gap:4px;}\n.fipt{font-size:11px;color:#5a4a7a;line-height:1.6;font-style:italic;}\n.ct-nbtn{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:8px;padding:6px 12px;font-size:10.5px;font-weight:600;color:rgba(255,255,255,.85);cursor:pointer;transition:background .15s;}\n.ct-nbtn:hover{background:rgba(255,255,255,.18);}\n\n.ct-overlay{display:none;position:fixed;inset:0;background:rgba(5,8,15,.7);backdrop-filter:blur(4px);z-index:1000;align-items:center;justify-content:center;padding:20px;}\n.ct-overlay.open{display:flex;}\n.ct-box{background:#0a1020;border:1px solid rgba(255,255,255,.08);border-radius:16px;max-width:560px;width:100%;max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.5);}\n.ct-header{position:sticky;top:0;background:#3d1a6e;padding:18px 22px;border-radius:16px 16px 0 0;display:flex;align-items:center;justify-content:space-between;z-index:5;}\n.ct-htitle{font-size:14px;font-weight:700;color:#fff;}\n.ct-hsub{font-size:11px;color:rgba(255,255,255,.55);margin-top:3px;}\n.ct-close{cursor:pointer;color:rgba(255,255,255,.55);font-size:20px;line-height:1;background:none;border:none;padding:4px;}\n.ct-close:hover{color:#fff;}\n.ct-body{padding:20px 22px;}\n\n.ct-field{margin-bottom:16px;}\n.ct-flabel{font-size:11px;font-weight:600;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.06em;margin-bottom:7px;display:block;}\n.ct-input{width:100%;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:9px 12px;font-size:13px;font-family:inherit;color:#fff;outline:none;}\n.ct-input::placeholder{color:rgba(255,255,255,.25);}\n.ct-input:focus{border-color:#3ecf7e;}\n.ct-textarea{width:100%;min-height:110px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:10px 12px;font-size:13px;font-family:inherit;color:#fff;resize:vertical;outline:none;}\n.ct-textarea::placeholder{color:rgba(255,255,255,.25);}\n.ct-textarea:focus{border-color:#3ecf7e;}\n\n.ct-lvrow{display:flex;gap:6px;}\n.ct-lv{flex:1;padding:8px;text-align:center;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid rgba(255,255,255,.1);color:rgba(255,255,255,.45);transition:all .15s;}\n.ct-lv:hover{border-color:rgba(255,255,255,.25);}\n.ct-lv.sel{background:#3d1a6e;color:#fff;border-color:#7c4de0;}\n\n.ct-reward{background:rgba(62,207,126,.08);border:1px solid rgba(62,207,126,.22);border-radius:10px;padding:13px 14px;margin-top:6px;display:flex;align-items:flex-start;gap:10px;}\n.ct-reward-icon{font-size:18px;color:#3ecf7e;flex-shrink:0;margin-top:1px;}\n.ct-reward-text{font-size:12px;color:rgba(255,255,255,.7);line-height:1.55;}\n.ct-reward-text b{color:#3ecf7e;font-weight:700;}\n\n.ct-submit{width:100%;background:#3ecf7e;color:#0a2a16;font-size:13px;font-weight:700;padding:12px;border-radius:9px;border:none;cursor:pointer;margin-top:18px;transition:background .15s;}\n.ct-submit:hover{background:#34b86c;}\n.ct-submit:disabled{background:rgba(62,207,126,.3);color:rgba(10,42,22,.5);cursor:not-allowed;}\n\n.ct-processing{display:none;text-align:center;padding:30px 10px;}\n.ct-processing.show{display:block;}\n.ct-spinner{width:32px;height:32px;border:3px solid rgba(62,207,126,.2);border-top-color:#3ecf7e;border-radius:50%;margin:0 auto 16px;animation:ct-spin 0.8s linear infinite;}\n@keyframes ct-spin{to{transform:rotate(360deg);}}\n.ct-processing-text{font-size:13px;color:rgba(255,255,255,.6);}\n\n.ct-form{display:block;}\n.ct-form.hide{display:none;}\n\n.ct-queue-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:rgba(255,255,255,.3);margin:0 0 10px;}\n.ct-qrow{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid rgba(255,255,255,.06);}\n.ct-qrow:last-child{border-bottom:none;}\n.ct-qname{font-size:12.5px;font-weight:600;color:#fff;}\n.ct-qmeta{font-size:10.5px;color:rgba(255,255,255,.35);margin-top:2px;}\n.ct-qstatus{font-size:9.5px;font-weight:700;padding:3px 9px;border-radius:20px;white-space:nowrap;margin-left:auto;}\n.ct-qstatus.pending{background:rgba(245,158,11,.12);color:#f59e0b;border:1px solid rgba(245,158,11,.25);}\n.ct-qstatus.approved{background:rgba(62,207,126,.12);color:#3ecf7e;border:1px solid rgba(62,207,126,.25);}\n.ct-qstatus.revision{background:rgba(248,113,113,.1);color:#f87171;border:1px solid rgba(248,113,113,.25);}\n\n\n.ct-toast{position:fixed;top:70px;right:20px;background:#3d1a6e;color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;z-index:9999;display:none;border-left:3px solid #3ecf7e;max-width:300px;line-height:1.5;}\n\n/* Updated CT styles with visibility toggle */\n.ct-nbtn{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:8px;padding:6px 12px;font-size:10.5px;font-weight:600;color:rgba(255,255,255,.85);cursor:pointer;transition:background .15s;}\n.ct-nbtn:hover{background:rgba(255,255,255,.18);}\n\n.ct-overlay{display:none;position:fixed;inset:0;background:rgba(5,8,15,.7);backdrop-filter:blur(4px);z-index:1000;align-items:center;justify-content:center;padding:20px;}\n.ct-overlay.open{display:flex;}\n.ct-box{background:#0a1020;border:1px solid rgba(255,255,255,.08);border-radius:16px;max-width:560px;width:100%;max-height:88vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.5);}\n.ct-header{position:sticky;top:0;background:#3d1a6e;padding:18px 22px;border-radius:16px 16px 0 0;display:flex;align-items:center;justify-content:space-between;z-index:5;}\n.ct-htitle{font-size:14px;font-weight:700;color:#fff;}\n.ct-hsub{font-size:11px;color:rgba(255,255,255,.55);margin-top:3px;}\n.ct-close{cursor:pointer;color:rgba(255,255,255,.55);font-size:20px;line-height:1;background:none;border:none;padding:4px;}\n.ct-close:hover{color:#fff;}\n.ct-body{padding:20px 22px;}\n\n.ct-field{margin-bottom:16px;}\n.ct-flabel{font-size:11px;font-weight:600;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:.06em;margin-bottom:7px;display:block;}\n.ct-input{width:100%;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:9px 12px;font-size:13px;font-family:inherit;color:#fff;outline:none;}\n.ct-input::placeholder{color:rgba(255,255,255,.25);}\n.ct-input:focus{border-color:#3ecf7e;}\n.ct-textarea{width:100%;min-height:110px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:10px 12px;font-size:13px;font-family:inherit;color:#fff;resize:vertical;outline:none;}\n.ct-textarea::placeholder{color:rgba(255,255,255,.25);}\n.ct-textarea:focus{border-color:#3ecf7e;}\n\n.ct-lvrow{display:flex;gap:6px;}\n.ct-lv{flex:1;padding:8px;text-align:center;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid rgba(255,255,255,.1);color:rgba(255,255,255,.45);transition:all .15s;}\n.ct-lv:hover{border-color:rgba(255,255,255,.25);}\n.ct-lv.sel{background:#3d1a6e;color:#fff;border-color:#7c4de0;}\n\n.ct-vizrow{display:flex;gap:6px;}\n.ct-viz{flex:1;display:flex;align-items:center;justify-content:center;gap:7px;padding:9px;text-align:center;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;border:1px solid rgba(255,255,255,.1);color:rgba(255,255,255,.45);transition:all .15s;}\n.ct-viz:hover{border-color:rgba(255,255,255,.25);}\n.ct-viz-icon{font-size:14px;}\n.ct-viz.sel-private{background:rgba(124,77,224,.18);color:#a78bfa;border-color:#7c4de0;}\n.ct-viz.sel-public{background:rgba(62,207,126,.15);color:#3ecf7e;border-color:#3ecf7e;}\n\n.ct-note{border-radius:10px;padding:13px 14px;margin-top:6px;display:flex;align-items:flex-start;gap:10px;}\n.ct-note-private{background:rgba(124,77,224,.08);border:1px solid rgba(124,77,224,.22);}\n.ct-note-private .ct-reward-icon{color:#a78bfa;}\n.ct-note-public{background:rgba(62,207,126,.08);border:1px solid rgba(62,207,126,.22);}\n\n.ct-reward{background:rgba(62,207,126,.08);border:1px solid rgba(62,207,126,.22);border-radius:10px;padding:13px 14px;margin-top:6px;display:flex;align-items:flex-start;gap:10px;}\n.ct-reward-icon{font-size:18px;color:#3ecf7e;flex-shrink:0;margin-top:1px;}\n.ct-reward-text{font-size:12px;color:rgba(255,255,255,.7);line-height:1.55;}\n.ct-reward-text b{color:#3ecf7e;font-weight:700;}\n\n.ct-submit{width:100%;background:#3ecf7e;color:#0a2a16;font-size:13px;font-weight:700;padding:12px;border-radius:9px;border:none;cursor:pointer;margin-top:18px;transition:background .15s;}\n.ct-submit:hover{background:#34b86c;}\n.ct-submit:disabled{background:rgba(62,207,126,.3);color:rgba(10,42,22,.5);cursor:not-allowed;}\n\n.ct-processing{display:none;text-align:center;padding:30px 10px;}\n.ct-processing.show{display:block;}\n.ct-spinner{width:32px;height:32px;border:3px solid rgba(62,207,126,.2);border-top-color:#3ecf7e;border-radius:50%;margin:0 auto 16px;animation:ct-spin 0.8s linear infinite;}\n@keyframes ct-spin{to{transform:rotate(360deg);}}\n.ct-processing-text{font-size:13px;color:rgba(255,255,255,.6);}\n\n.ct-form{display:block;}\n.ct-form.hide{display:none;}\n\n.ct-queue-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:rgba(255,255,255,.3);margin:0 0 10px;}\n.ct-qrow{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid rgba(255,255,255,.06);}\n.ct-qrow:last-child{border-bottom:none;}\n.ct-qname{font-size:12.5px;font-weight:600;color:#fff;}\n.ct-qmeta{display:flex;align-items:center;gap:4px;font-size:10.5px;color:rgba(255,255,255,.35);margin-top:2px;}\n.ct-qviz-icon{font-size:11px;}\n.ct-qstatus{font-size:9.5px;font-weight:700;padding:3px 9px;border-radius:20px;white-space:nowrap;margin-left:auto;}\n.ct-qstatus.pending{background:rgba(245,158,11,.12);color:#f59e0b;border:1px solid rgba(245,158,11,.25);}\n.ct-qstatus.approved{background:rgba(62,207,126,.12);color:#3ecf7e;border:1px solid rgba(62,207,126,.25);}\n.ct-qstatus.revision{background:rgba(248,113,113,.1);color:#f87171;border:1px solid rgba(248,113,113,.25);}\n.ct-qstatus.private{background:rgba(124,77,224,.12);color:#a78bfa;border:1px solid rgba(124,77,224,.25);}\n\n/* Assign Tactic styles */\n.at-nbtn{font-size:11px;font-weight:600;padding:6px 12px;border-radius:7px;cursor:pointer;white-space:nowrap;border:1px solid transparent;transition:all .15s;background:rgba(61,26,110,.06);color:var(--navy);border-color:rgba(61,26,110,.15);}\n.at-nbtn:hover{background:rgba(61,26,110,.12);}\n\n.at-overlay{display:none;position:fixed;inset:0;background:rgba(5,8,15,.6);backdrop-filter:blur(4px);z-index:1001;align-items:center;justify-content:center;padding:20px;}\n.at-overlay.open{display:flex;}\n.at-box{background:#0a1020;border:1px solid rgba(255,255,255,.08);border-radius:16px;max-width:480px;width:100%;max-height:86vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.5);}\n.at-header{position:sticky;top:0;background:#3d1a6e;padding:18px 22px;border-radius:16px 16px 0 0;display:flex;align-items:center;justify-content:space-between;z-index:5;}\n.at-htitle{font-size:14px;font-weight:700;color:#fff;}\n.at-hsub{font-size:11px;color:rgba(255,255,255,.55);margin-top:3px;}\n.at-close{cursor:pointer;color:rgba(255,255,255,.55);font-size:20px;line-height:1;background:none;border:none;padding:4px;}\n.at-close:hover{color:#fff;}\n.at-body{padding:20px 22px;}\n\n.at-student{display:flex;align-items:center;gap:11px;background:rgba(255,255,255,.04);border-radius:10px;padding:11px 13px;margin-bottom:16px;}\n.at-student-avatar{width:34px;height:34px;border-radius:50%;background:#d4f5e5;color:#2aad62;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0;}\n.at-student-name{font-size:12.5px;font-weight:700;color:#fff;}\n.at-student-sub{font-size:10.5px;color:rgba(255,255,255,.45);margin-top:1px;}\n\n.at-search{width:100%;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:9px 12px;font-size:13px;font-family:inherit;color:#fff;outline:none;margin-bottom:12px;}\n.at-search::placeholder{color:rgba(255,255,255,.25);}\n.at-search:focus{border-color:#3ecf7e;}\n\n.at-tab-row{display:flex;gap:6px;margin-bottom:12px;}\n.at-tab{padding:6px 13px;border-radius:20px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid rgba(255,255,255,.1);color:rgba(255,255,255,.4);}\n.at-tab.sel{background:#3d1a6e;color:#fff;border-color:#7c4de0;}\n\n.at-list{display:flex;flex-direction:column;gap:6px;margin-bottom:16px;max-height:260px;overflow-y:auto;}\n.at-item{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:9px;padding:9px 11px;cursor:pointer;transition:all .15s;}\n.at-item:hover{border-color:rgba(255,255,255,.2);}\n.at-item.sel{border-color:#3ecf7e;background:rgba(62,207,126,.08);}\n.at-icon{width:26px;height:26px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;}\n.at-icon.priv{background:rgba(124,77,224,.2);color:#a78bfa;}\n.at-icon.lib{background:rgba(62,207,126,.15);color:#3ecf7e;}\n.at-text{flex:1;min-width:0;}\n.at-name{font-size:11.5px;font-weight:700;color:#fff;}\n.at-meta{font-size:9.5px;color:rgba(255,255,255,.4);margin-top:1px;}\n.at-check{width:18px;height:18px;border-radius:50%;border:1.5px solid rgba(255,255,255,.2);flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:10px;color:transparent;}\n.at-item.sel .at-check{background:#3ecf7e;border-color:#3ecf7e;color:#0a2a16;}\n\n.at-empty{text-align:center;padding:24px 10px;font-size:12px;color:rgba(255,255,255,.3);}\n\n.at-submit{width:100%;background:#3ecf7e;color:#0a2a16;font-size:13px;font-weight:700;padding:12px;border-radius:9px;border:none;cursor:pointer;transition:background .15s;}\n.at-submit:hover{background:#34b86c;}\n\n</style>\n</head>\n<body>\n<div class="ct-toast" id="ctToast"></div>\n<div class="app">\n  <div class="nav">\n    <div class="nav-l">\n      <div class="logo">\n        <svg width="22" height="22" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="3.5"/><circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="3.5"/><circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="3.5"/><path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/></svg>\n        Orbis <em>AI</em>\n      </div>\n      <div class="ndiv"></div>\n      <div class="nsub">Padel tactical simulator · 2.5D</div>\n    </div>\n    <div class="nav-r">\n      <div class="npill">FIP Academy</div>\n      <div class="nbtn" onclick="openCreateTactic()" style="background:rgba(62,207,126,.12);border-color:rgba(62,207,126,.3);color:#3ecf7e;">+ Create tactic</div>\n      <div class="nbtn" onclick="openLibrary()">🔍 Browse +300 plays</div>\n      <div class="nbtn" onclick="window.location.href=\'/demo/coach\'">← Coach hub</div>\n    </div>\n  </div>\n\n  <div class="lbar">\n    <div class="lv lg" onclick="setLevel(0)" id="lv0">● Beginner</div>\n    <div class="lv" onclick="setLevel(1)" id="lv1">○ Intermediate</div>\n    <div class="lv" onclick="setLevel(2)" id="lv2">○ Advanced</div>\n    <div class="lsep"></div>\n    <div class="lcnt" id="lcnt">Play 1 of 6</div>\n  </div>\n\n  <div class="pbar" id="pbar"></div>\n\n  <div class="body">\n    <div class="cpanel">\n      <div class="cglow"></div>\n      <div class="cwrap">\n        <canvas id="court"></canvas>\n      </div>\n      <div class="shotbar">\n        <div class="sdot" id="sdot"></div>\n        <div class="stxt" id="stxt">Press Play to start</div>\n        <div class="sbadge" id="sbadge"></div>\n      </div>\n      <div class="ctrl">\n        <div style="display:flex;align-items:center;gap:10px;flex:1;">\n          <button class="playbtn" id="playbtn" onclick="togglePlay()">\n            <svg id="playicon" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg>\n          </button>\n          <div class="ptrack" id="ptrack">\n            <div class="pfill" id="pfill"></div>\n            <div class="pthumb" id="pthumb"></div>\n          </div>\n          <div class="pmeta" id="pmeta">— / —</div>\n        </div>\n        <div class="cbtns">\n          <div class="cbtn" onclick="prevShot()">← Prev</div>\n          <div class="cbtn" onclick="nextShot()">Next →</div>\n          <div class="cbtn cg" id="autobtn" onclick="toggleAuto()">▶ Auto</div>\n        </div>\n      </div>\n    </div>\n\n    <div class="rp">\n      <div class="rps">\n        <div class="rpl">Current play</div>\n        <div class="rpname" id="rpname">—</div>\n        <div class="rptags" id="rptags"></div>\n        <div class="rpdesc" id="rpdesc"></div>\n      </div>\n      <div class="rpseq" id="rpseq"></div>\n      <div class="fip">\n        <div class="fipl"><div style="width:4px;height:4px;border-radius:50%;background:#7c4de0;flex-shrink:0;"></div><span id="fiplvl">FIP Level 1</span></div>\n        <div class="fipt" id="fipt"></div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<script>\n// ── DATA ─────────────────────────────────────────────────────────────────────\nconst LEVELS=[\n{id:\'beginner\',label:\'Beginner\',dot:\'#4ade80\',cls:\'lg\',sym:\'●\',\nplays:[\n{name:\'Serve + net rush\',type:\'Offensive\',fip:\'FIP Level 1\',\ndesc:\'Serve down the T, both players sprint to net. Goal: own the net before opponents settle.\',\nfipText:\'In padel, the serve is a transition tool — the goal is to reach net, not win the point with the serve.\',\nsY:[{x:.32,y:.88},{x:.68,y:.88}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Serve down the T\',h:\'Y\',f:{x:.68,y:.88},c:{x:.5,y:.65},t:{x:.5,y:.12},ht:.15,d:1100,yP:[{x:.32,y:.88},{x:.68,y:.88}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Both sprint to net\',h:\'M\',f:{x:.5,y:.12},t:{x:.5,y:.12},ht:0,d:900,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents return cross-court\',h:\'O\',f:{x:.28,y:.14},c:{x:.55,y:.4},t:{x:.65,y:.62},ht:.1,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Volley winner — open court\',h:\'Y\',f:{x:.65,y:.6},c:{x:.4,y:.35},t:{x:.15,y:.1},ht:.05,d:750,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Lob + net rush\',type:\'Offensive\',fip:\'FIP Level 1\',\ndesc:\'Pinned at baseline, hit a deep lob over opponents and both sprint to net. Classic defensive-to-attack transition.\',\nfipText:\'The lob followed by net rush is the fundamental baseline-to-net transition. Time your sprint to the lob arc.\',\nsY:[{x:.32,y:.86},{x:.68,y:.86}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents drive at you\',h:\'O\',f:{x:.28,y:.14},c:{x:.4,y:.5},t:{x:.35,y:.82},ht:.05,d:900,yP:[{x:.32,y:.86},{x:.68,y:.86}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'LOB — deep over opponents\',h:\'Y\',f:{x:.35,y:.82},c:{x:.5,y:.22},t:{x:.5,y:.07},ht:.9,d:1800,yP:[{x:.32,y:.86},{x:.68,y:.86}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Sprint to net — both players\',h:\'M\',f:{x:.5,y:.07},t:{x:.5,y:.07},ht:0,d:900,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.07},{x:.72,y:.07}]},\n{l:\'Opponents scramble — weak reply\',h:\'O\',f:{x:.5,y:.07},c:{x:.45,y:.35},t:{x:.42,y:.62},ht:.2,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.07},{x:.72,y:.07}]},\n{l:\'Volley winner\',h:\'Y\',f:{x:.42,y:.6},c:{x:.5,y:.32},t:{x:.5,y:.08},ht:.05,d:750,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.07},{x:.72,y:.07}],w:true}\n]},\n{name:\'Deep cross-court lob\',type:\'Defensive\',fip:\'FIP Level 1\',\ndesc:\'From baseline, lob cross-court to the deepest corner. Opponent must travel maximum distance.\',\nfipText:\'Always lob cross-court and deep. A short lob is punished; a deep cross-court lob forces maximum opponent movement.\',\nsY:[{x:.32,y:.84},{x:.68,y:.84}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents drive to your left\',h:\'O\',f:{x:.72,y:.14},c:{x:.45,y:.5},t:{x:.32,y:.8},ht:.08,d:950,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Deep cross-court LOB\',h:\'Y\',f:{x:.32,y:.8},c:{x:.72,y:.3},t:{x:.85,y:.07},ht:.85,d:1900,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponent forced back — weak overhead\',h:\'O\',f:{x:.85,y:.07},c:{x:.6,y:.4},t:{x:.55,y:.8},ht:.2,d:1100,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.85,y:.08},{x:.45,y:.14}]},\n{l:\'LOB again — deep parallel\',h:\'Y\',f:{x:.55,y:.8},c:{x:.55,y:.35},t:{x:.82,y:.07},ht:.8,d:1700,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.85,y:.08},{x:.45,y:.14}]}\n]},\n{name:\'Middle volley attack\',type:\'Offensive\',fip:\'FIP Level 1\',\ndesc:\'Both players at net attack consecutively down the middle corridor between opponents.\',\nfipText:\'The middle is the most dangerous zone in padel. Neither opponent has clear authority — attack it consistently.\',\nsY:[{x:.32,y:.57},{x:.68,y:.57}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents play cross-court ball\',h:\'O\',f:{x:.28,y:.14},c:{x:.55,y:.38},t:{x:.65,y:.62},ht:.08,d:950,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'First volley — down the middle\',h:\'Y\',f:{x:.65,y:.6},c:{x:.5,y:.38},t:{x:.5,y:.16},ht:.05,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents weak central reply\',h:\'O\',f:{x:.5,y:.16},c:{x:.5,y:.4},t:{x:.5,y:.65},ht:.15,d:900,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'VOLLEY WINNER — middle\',h:\'Y\',f:{x:.5,y:.62},c:{x:.5,y:.38},t:{x:.5,y:.12},ht:.04,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Defensive lob rotation\',type:\'Defensive\',fip:\'FIP Level 1\',\ndesc:\'Both players rotate lobs patiently from baseline. Alternate cross-court and parallel. Wait for errors.\',\nfipText:\'Patient baseline defense wins points at beginner level. Opponents will make overhead errors if you keep the ball deep and vary direction.\',\nsY:[{x:.32,y:.84},{x:.68,y:.84}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents smash from net\',h:\'O\',f:{x:.32,y:.14},c:{x:.4,y:.5},t:{x:.36,y:.82},ht:.05,d:800,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Cross-court LOB — deep right\',h:\'Y\',f:{x:.36,y:.82},c:{x:.72,y:.32},t:{x:.82,y:.07},ht:.82,d:1800,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents bandeja back center\',h:\'O\',f:{x:.82,y:.07},c:{x:.5,y:.38},t:{x:.45,y:.84},ht:.2,d:1100,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Parallel LOB — down the line\',h:\'Y\',f:{x:.45,y:.84},c:{x:.45,y:.38},t:{x:.75,y:.07},ht:.8,d:1700,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Overhead error — point won!\',h:\'O\',f:{x:.75,y:.07},c:{x:.6,y:.5},t:{x:.95,y:.95},ht:.05,d:800,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}],e:true}\n]},\n{name:\'Recovery lob\',type:\'Defensive\',fip:\'FIP Level 1\',\ndesc:\'Under pressure with no time to construct — play a high defensive lob to buy time and reset.\',\nfipText:\'When in doubt — LOB. The globo always gives you time to recover position and restart the point from neutral.\',\nsY:[{x:.32,y:.82},{x:.68,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Hard drive at body — no time\',h:\'O\',f:{x:.5,y:.14},c:{x:.5,y:.5},t:{x:.5,y:.78},ht:.04,d:750,yP:[{x:.32,y:.82},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'RECOVERY LOB — high and deep\',h:\'Y\',f:{x:.5,y:.78},c:{x:.35,y:.25},t:{x:.28,y:.07},ht:.9,d:1900,yP:[{x:.32,y:.82},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Reposition at baseline\',h:\'M\',f:{x:.28,y:.07},t:{x:.28,y:.07},ht:0,d:700,yP:[{x:.3,y:.84},{x:.7,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents bandeja — controlled\',h:\'O\',f:{x:.28,y:.07},c:{x:.45,y:.38},t:{x:.48,y:.82},ht:.18,d:1100,yP:[{x:.3,y:.84},{x:.7,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Cross-court LOB — now in control\',h:\'Y\',f:{x:.48,y:.82},c:{x:.75,y:.3},t:{x:.85,y:.07},ht:.82,d:1700,yP:[{x:.3,y:.84},{x:.7,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]}\n]}\n]},\n{id:\'intermediate\',label:\'Intermediate\',dot:\'#fbbf24\',cls:\'li\',sym:\'○\',\nplays:[\n{name:\'Chiquita + advance\',type:\'Neutral\',fip:\'FIP Level 2\',\ndesc:\'Play a chiquita at the net player\\\'s feet, then immediately advance to net. The chiquita is a transition shot — always follow it.\',\nfipText:\'FIP Level 2: The chiquita is a transition shot — if you don\\\'t follow it to net, you\\\'ve wasted it. Always advance after the chiquita.\',\nsY:[{x:.3,y:.74},{x:.7,y:.74}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents attack — fast low ball\',h:\'O\',f:{x:.28,y:.14},c:{x:.35,y:.5},t:{x:.35,y:.7},ht:.04,d:850,yP:[{x:.3,y:.74},{x:.7,y:.74}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'CHIQUITA — low at net player\\\'s feet\',h:\'Y\',f:{x:.35,y:.7},c:{x:.32,y:.52},t:{x:.3,y:.3},ht:.04,d:900,yP:[{x:.3,y:.74},{x:.7,y:.74}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Advance to net — both players\',h:\'M\',f:{x:.3,y:.3},t:{x:.3,y:.3},ht:0,d:800,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Forced volley up — weak reply\',h:\'O\',f:{x:.28,y:.18},c:{x:.48,y:.4},t:{x:.52,y:.65},ht:.3,d:1100,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'CROSS VOLLEY WINNER\',h:\'Y\',f:{x:.52,y:.62},c:{x:.72,y:.35},t:{x:.88,y:.1},ht:.06,d:700,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Lob + chiquita mix\',type:\'Neutral\',fip:\'FIP Level 2\',\ndesc:\'Alternate lobs and chiquitas — never two consecutive lobs. Keeps net players constantly repositioning.\',\nfipText:\'FIP Level 2: Lob + chiquita alternation is the most important pattern for baseline players. Predictable defense is exploitable.\',\nsY:[{x:.3,y:.82},{x:.7,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents drive at you\',h:\'O\',f:{x:.5,y:.14},c:{x:.5,y:.5},t:{x:.5,y:.78},ht:.06,d:900,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'LOB — push opponents back\',h:\'Y\',f:{x:.5,y:.78},c:{x:.5,y:.3},t:{x:.5,y:.08},ht:.85,d:1800,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Bandeja — coming forward again\',h:\'O\',f:{x:.5,y:.08},c:{x:.5,y:.38},t:{x:.5,y:.78},ht:.2,d:1100,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.16}]},\n{l:\'CHIQUITA — catches them mid-court\',h:\'Y\',f:{x:.5,y:.78},c:{x:.5,y:.58},t:{x:.5,y:.38},ht:.04,d:850,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.16}]},\n{l:\'Advance to net\',h:\'M\',f:{x:.5,y:.38},t:{x:.5,y:.38},ht:0,d:750,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.16},{x:.7,y:.16}]},\n{l:\'Weak reply from opponents\',h:\'O\',f:{x:.3,y:.2},c:{x:.45,y:.4},t:{x:.45,y:.65},ht:.25,d:1000,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.16},{x:.7,y:.16}]},\n{l:\'VOLLEY WINNER\',h:\'Y\',f:{x:.45,y:.62},c:{x:.5,y:.35},t:{x:.85,y:.08},ht:.05,d:700,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.16},{x:.7,y:.16}],w:true}\n]},\n{name:\'Bandeja hold at net\',type:\'Neutral\',fip:\'FIP Level 2\',\ndesc:\'When lobbed, play a bandeja (tray shot) wide to the glass to maintain net position rather than attacking.\',\nfipText:\'FIP Level 2: The bandeja is THE signature padel shot. Its goal is not to win — it\\\'s to hold net position and force another lob.\',\nsY:[{x:.32,y:.57},{x:.68,y:.57}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'You attack — cross-court volley\',h:\'Y\',f:{x:.32,y:.57},c:{x:.55,y:.35},t:{x:.72,y:.12},ht:.05,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents LOB over your head\',h:\'O\',f:{x:.72,y:.12},c:{x:.5,y:.4},t:{x:.5,y:.76},ht:.82,d:1800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Right player drops back\',h:\'M\',f:{x:.5,y:.76},t:{x:.5,y:.76},ht:0,d:600,yP:[{x:.32,y:.57},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'BANDEJA — wide to side glass\',h:\'Y\',f:{x:.68,y:.76},c:{x:.88,y:.45},t:{x:.92,y:.12},ht:.12,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Recover to net\',h:\'M\',f:{x:.92,y:.12},t:{x:.92,y:.12},ht:0,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents LOB again\',h:\'O\',f:{x:.92,y:.12},c:{x:.6,y:.38},t:{x:.45,y:.78},ht:.78,d:1700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'SECOND BANDEJA — holding net\',h:\'Y\',f:{x:.45,y:.74},c:{x:.3,y:.45},t:{x:.15,y:.12},ht:.12,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]}\n]},\n{name:\'Vibora cross-court\',type:\'Offensive\',fip:\'FIP Level 2-3\',\ndesc:\'High ball at center court — attack with a vibora (viper shot) with sidespin to the far side glass.\',\nfipText:\'FIP Level 2-3: Cross-court vibora angles the ball into the corner after the glass — the standard professional direction for this shot.\',\nsY:[{x:.28,y:.64},{x:.68,y:.62}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'You drive cross-court\',h:\'Y\',f:{x:.28,y:.64},c:{x:.6,y:.42},t:{x:.72,y:.12},ht:.15,d:1000,yP:[{x:.28,y:.64},{x:.68,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents LOB back — high center\',h:\'O\',f:{x:.72,y:.12},c:{x:.58,y:.4},t:{x:.65,y:.58},ht:.8,d:1700,yP:[{x:.28,y:.64},{x:.68,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'VIBORA — cutting to side glass\',h:\'Y\',f:{x:.65,y:.56},c:{x:.95,y:.35},t:{x:.97,y:.09},ht:.08,d:700,yP:[{x:.28,y:.64},{x:.68,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Chiquita + lob rotation\',type:\'Defensive\',fip:\'FIP Level 2\',\ndesc:\'Alternate lob and chiquita — never predictable. Forces net players to constantly adjust their feet.\',\nfipText:\'FIP Level 2: Directional and tactical variety prevents opponents from pre-positioning. Two consecutive lobs of the same type are always exploitable.\',\nsY:[{x:.3,y:.82},{x:.7,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents push — hard flat drive\',h:\'O\',f:{x:.72,y:.14},c:{x:.55,y:.5},t:{x:.58,y:.8},ht:.04,d:800,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'LOB #1 — parallel deep\',h:\'Y\',f:{x:.58,y:.8},c:{x:.6,y:.35},t:{x:.78,y:.07},ht:.82,d:1700,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Bandeja — coming forward\',h:\'O\',f:{x:.78,y:.07},c:{x:.55,y:.38},t:{x:.52,y:.8},ht:.18,d:1100,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.14}]},\n{l:\'CHIQUITA — catches them moving in\',h:\'Y\',f:{x:.52,y:.8},c:{x:.48,y:.6},t:{x:.46,y:.36},ht:.04,d:850,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.14}]},\n{l:\'Weak volley up from net player\',h:\'O\',f:{x:.3,y:.2},c:{x:.45,y:.44},t:{x:.5,y:.78},ht:.35,d:1100,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.14}]},\n{l:\'LOB #2 — cross-court deep\',h:\'Y\',f:{x:.5,y:.78},c:{x:.78,y:.3},t:{x:.85,y:.07},ht:.8,d:1700,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.14}]}\n]},\n{name:\'Drive + net rush\',type:\'Offensive\',fip:\'FIP Level 2\',\ndesc:\'When opponents are slightly off net, strike a low flat drive at their feet then sprint to net behind the shot.\',\nfipText:\'FIP Level 2: The drive is underused in modern padel. When opponents are out of position, a flat drive + rush is more direct than a chiquita.\',\nsY:[{x:.3,y:.76},{x:.7,y:.76}],sO:[{x:.3,y:.18},{x:.7,y:.18}],\nshots:[\n{l:\'Opponents slightly off net\',h:\'O\',f:{x:.3,y:.18},c:{x:.45,y:.5},t:{x:.42,y:.74},ht:.06,d:900,yP:[{x:.3,y:.76},{x:.7,y:.76}],oP:[{x:.3,y:.18},{x:.7,y:.18}]},\n{l:\'DRIVE — flat low at their feet\',h:\'Y\',f:{x:.42,y:.74},c:{x:.35,y:.52},t:{x:.3,y:.32},ht:.03,d:800,yP:[{x:.3,y:.76},{x:.7,y:.76}],oP:[{x:.3,y:.18},{x:.7,y:.18}]},\n{l:\'Sprint to net behind the drive\',h:\'M\',f:{x:.3,y:.32},t:{x:.3,y:.32},ht:0,d:800,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.18}]},\n{l:\'Forced weak low volley reply\',h:\'O\',f:{x:.3,y:.22},c:{x:.45,y:.42},t:{x:.5,y:.65},ht:.3,d:1000,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.18}]},\n{l:\'PARALLEL VOLLEY WINNER\',h:\'Y\',f:{x:.5,y:.62},c:{x:.35,y:.38},t:{x:.12,y:.1},ht:.05,d:700,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.18}],w:true}\n]}\n]},\n{id:\'advanced\',label:\'Advanced\',dot:\'#f87171\',cls:\'lr\',sym:\'○\',\nplays:[\n{name:\'Full point pattern — pro\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Complete professional sequence: serve → approach volley → bandeja → chiquita pressure → vibora winner. Five-shot architecture.\',\nfipText:\'FIP Level 3: Point construction patterns — pre-planned 5-shot sequences — are how professional pairs approach every point systematically.\',\nsY:[{x:.32,y:.88},{x:.68,y:.88}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'(1) Body serve to weaker player\',h:\'Y\',f:{x:.68,y:.88},c:{x:.35,y:.65},t:{x:.28,y:.12},ht:.15,d:1000,yP:[{x:.32,y:.88},{x:.68,y:.88}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Rush to net\',h:\'M\',f:{x:.28,y:.12},t:{x:.28,y:.12},ht:0,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(2) Opponent lobs — deep\',h:\'O\',f:{x:.28,y:.14},c:{x:.5,y:.35},t:{x:.5,y:.72},ht:.78,d:1700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(3) BANDEJA — hold net position\',h:\'Y\',f:{x:.5,y:.68},c:{x:.75,y:.42},t:{x:.88,y:.1},ht:.12,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Recover to net\',h:\'M\',f:{x:.88,y:.1},t:{x:.88,y:.1},ht:0,d:600,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(4) Opponents push flat drive\',h:\'O\',f:{x:.88,y:.1},c:{x:.6,y:.42},t:{x:.55,y:.62},ht:.05,d:850,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(5) VIBORA — cutting winner\',h:\'Y\',f:{x:.55,y:.6},c:{x:.95,y:.35},t:{x:.97,y:.09},ht:.08,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Vibora to side glass\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Hit vibora with sidespin into the side glass — ball bounces at a sharp low angle opponents cannot reach.\',\nfipText:\'FIP Level 3: Vibora into the side glass is the professional standard winner. The ball dies in a zone opponents cannot position for.\',\nsY:[{x:.28,y:.62},{x:.7,y:.6}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Rally — drive cross-court\',h:\'Y\',f:{x:.28,y:.62},c:{x:.6,y:.4},t:{x:.72,y:.12},ht:.12,d:1000,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents LOB — high ball center\',h:\'O\',f:{x:.72,y:.12},c:{x:.58,y:.38},t:{x:.62,y:.56},ht:.82,d:1700,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'VIBORA — to side glass parallel\',h:\'Y\',f:{x:.62,y:.54},c:{x:.97,y:.4},t:{x:.97,y:.1},ht:.07,d:700,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Ball dies off glass — point won\',h:\'Y\',f:{x:.97,y:.1},c:{x:.8,y:.15},t:{x:.65,y:.22},ht:0,d:600,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.72,y:.14},{x:.88,y:.22}],w:true}\n]},\n{name:\'Bajada — aggressive wall exit\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Take overhead off the back glass early on the way down — hit flat with forward pressure rather than waiting.\',\nfipText:\'FIP Level 3: The bajada is taken early on the way down from the glass — high risk, high reward. Only when the ball is cleanly above you.\',\nsY:[{x:.32,y:.57},{x:.68,y:.57}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents LOB — deep to back glass\',h:\'O\',f:{x:.5,y:.14},c:{x:.5,y:.45},t:{x:.5,y:.84},ht:.88,d:1900,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Drop back to intercept\',h:\'M\',f:{x:.5,y:.84},t:{x:.5,y:.84},ht:0,d:600,yP:[{x:.32,y:.78},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'BAJADA — take early off glass\',h:\'Y\',f:{x:.5,y:.82},c:{x:.5,y:.55},t:{x:.5,y:.12},ht:.25,d:1100,yP:[{x:.32,y:.78},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Recover to net\',h:\'M\',f:{x:.5,y:.12},t:{x:.5,y:.12},ht:0,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents scramble — weak reply\',h:\'O\',f:{x:.5,y:.12},c:{x:.48,y:.4},t:{x:.45,y:.65},ht:.2,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'FINISH — volley winner\',h:\'Y\',f:{x:.45,y:.62},c:{x:.5,y:.35},t:{x:.5,y:.1},ht:.04,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Defense → lob → chiquita → net\',type:\'Neutral\',fip:\'FIP Level 3\',\ndesc:\'Three-shot conversion: lob for time → chiquita for pressure → advance to net and finish. The pro defensive-to-attack sequence.\',\nfipText:\'FIP Level 3: The three-touch net takeover is the benchmark advanced pattern. Each shot has a specific purpose — time, pressure, position.\',\nsY:[{x:.32,y:.84},{x:.68,y:.84}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents smash hard\',h:\'O\',f:{x:.5,y:.14},c:{x:.5,y:.5},t:{x:.5,y:.8},ht:.04,d:750,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(1) LOB — create time\',h:\'Y\',f:{x:.5,y:.8},c:{x:.38,y:.28},t:{x:.28,y:.08},ht:.88,d:1900,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents bandeja coming forward\',h:\'O\',f:{x:.28,y:.08},c:{x:.48,y:.4},t:{x:.48,y:.82},ht:.2,d:1100,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.3,y:.18},{x:.7,y:.14}]},\n{l:\'(2) CHIQUITA — pressure at feet\',h:\'Y\',f:{x:.48,y:.82},c:{x:.42,y:.62},t:{x:.38,y:.36},ht:.04,d:900,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.3,y:.18},{x:.7,y:.14}]},\n{l:\'(3) Advance to net — both\',h:\'M\',f:{x:.38,y:.36},t:{x:.38,y:.36},ht:0,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.14}]},\n{l:\'Forced weak volley from net player\',h:\'O\',f:{x:.3,y:.22},c:{x:.48,y:.42},t:{x:.52,y:.68},ht:.32,d:1100,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.14}]},\n{l:\'NET WINNER — cross volley\',h:\'Y\',f:{x:.52,y:.65},c:{x:.72,y:.38},t:{x:.88,y:.1},ht:.05,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.14}],w:true}\n]},\n{name:\'Around the post\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Cornered wide at side glass with a low ball — hit it around the net post rather than over. 100% legal.\',\nfipText:\'FIP Level 3: Around-the-post (por el palo) is legal in padel and occasionally used by professionals when the angle makes it the optimal shot.\',\nsY:[{x:.3,y:.82},{x:.68,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents angle vibora — wide left\',h:\'O\',f:{x:.32,y:.14},c:{x:.1,y:.45},t:{x:.06,y:.74},ht:.08,d:900,yP:[{x:.3,y:.82},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Chase to far left wall\',h:\'M\',f:{x:.06,y:.74},t:{x:.06,y:.74},ht:0,d:600,yP:[{x:.06,y:.75},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'AROUND THE POST — por el palo!\',h:\'Y\',f:{x:.06,y:.74},c:{x:-.02,y:.52},t:{x:.08,y:.2},ht:.04,d:950,yP:[{x:.06,y:.75},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Australian + switch\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Both line up same side before serve. Net player crosses to opposite side immediately as serve lands — misdirection.\',\nfipText:\'FIP Level 3: Australian formation misdirection gives the serving pair a tactical advantage on the first volley by confusing the receiver\\\'s read.\',\nsY:[{x:.55,y:.88},{x:.55,y:.72}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Australian — both left side\',h:\'M\',f:{x:.55,y:.72},t:{x:.55,y:.72},ht:0,d:400,yP:[{x:.55,y:.88},{x:.55,y:.72}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Serve wide right\',h:\'Y\',f:{x:.55,y:.88},c:{x:.72,y:.62},t:{x:.72,y:.12},ht:.15,d:1000,yP:[{x:.55,y:.88},{x:.55,y:.72}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Net player SWITCHES to right\',h:\'M\',f:{x:.72,y:.12},t:{x:.72,y:.12},ht:0,d:700,yP:[{x:.35,y:.62},{x:.72,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponent confused — cross return\',h:\'O\',f:{x:.72,y:.12},c:{x:.42,y:.4},t:{x:.32,y:.65},ht:.1,d:1000,yP:[{x:.35,y:.62},{x:.72,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Left player intercepts — WINNER\',h:\'Y\',f:{x:.32,y:.63},c:{x:.5,y:.38},t:{x:.88,y:.1},ht:.05,d:750,yP:[{x:.35,y:.62},{x:.72,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]}\n]}\n];\n\n// ── STATE ─────────────────────────────────────────────────────────────────────\nlet lvl=0,play=0,shot=0,playing=false;\nlet animId=null,autoTimer=null,shotStart=null,shotT=0;\n\nfunction getPlay(){return LEVELS[lvl].plays[play];}\nfunction getShots(){return getPlay().shots;}\n\n// ── CANVAS SETUP ──────────────────────────────────────────────────────────────\nconst canvas=document.getElementById(\'court\');\nlet CW,CH,ML,MR,MT,MB,CX,CY,CW2,CH2;\n\nfunction setupCanvas(){\n  const wrap=document.querySelector(\'.cwrap\');\n  const W=wrap.clientWidth,H=wrap.clientHeight;\n  // 2.5D court: perspective quad\n  // wider at bottom, narrower at top\n  // We need space for perspective + glass walls\n  const cH=Math.max(200,Math.min(H-10,W*1.3));\n  const cW=Math.max(160,Math.min(W-10,cH/1.3));\n  const dpr=window.devicePixelRatio||1;\n  canvas.width=cW*dpr;canvas.height=cH*dpr;\n  canvas.style.width=cW+\'px\';\n  canvas.style.height=cH+\'px\';\n  canvas.getContext(\'2d\').setTransform(dpr,0,0,dpr,0,0);\n  CW=cW;CH=cH;\n  // Perspective court corners:\n  // TL=(CW*0.22,CH*0.06) TR=(CW*0.78,CH*0.06)\n  // BL=(CW*0.04,CH*0.94) BR=(CW*0.96,CH*0.94)\n}\n\n// Convert normalized padel coords to perspective screen coords\n// x: 0=left, 1=right; y: 0=top (opponents back), 1=bottom (your back)\nfunction toScreen(nx,ny){\n  // Interpolate between top edge and bottom edge\n  const topL={x:CW*0.22,y:CH*0.055};\n  const topR={x:CW*0.78,y:CH*0.055};\n  const botL={x:CW*0.04,y:CH*0.945};\n  const botR={x:CW*0.96,y:CH*0.945};\n  const lx=topL.x+(botL.x-topL.x)*ny;\n  const ly=topL.y+(botL.y-topL.y)*ny;\n  const rx=topR.x+(botR.x-topR.x)*ny;\n  const ry=topR.y+(botR.y-topR.y)*ny;\n  return{x:lx+(rx-lx)*nx,y:ly+(ry-ly)*nx+(ry-ly)*0};\n}\n// Actually simpler — for a trapezoid:\nfunction sc(nx,ny){\n  const tLx=CW*0.22,tLy=CH*0.055,tRx=CW*0.78,tRy=CH*0.055;\n  const bLx=CW*0.04,bLy=CH*0.945,bRx=CW*0.96,bRy=CH*0.945;\n  const lx=tLx+(bLx-tLx)*ny, ly=tLy+(bLy-tLy)*ny;\n  const rx=tRx+(bRx-tRx)*ny, ry=tRy+(bRy-tRy)*ny;\n  const sx=lx+(rx-lx)*nx, sy=ly+(ry-ly)*nx + (ry-ly)*(0);\n  // Y pos is purely based on ny for the trapezoid:\n  const px=lx+(rx-lx)*nx;\n  const py=tLy+(bLy-tLy)*ny;\n  return{x:px,y:py};\n}\n\nfunction lerp(a,b,t){return a+(b-a)*t;}\nfunction ease(t){return t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;}\nfunction bez(p0,p1,p2,t){\n  return{x:(1-t)*(1-t)*p0.x+2*(1-t)*t*p1.x+t*t*p2.x,\n         y:(1-t)*(1-t)*p0.y+2*(1-t)*t*p1.y+t*t*p2.y};\n}\n\n// ── DRAW ─────────────────────────────────────────────────────────────────────\nfunction drawCourt(ctx){\n  const tL=sc(0,0),tR=sc(1,0),bL=sc(0,1),bR=sc(1,1);\n  const tLx=CW*0.22,tRx=CW*0.78,tY=CH*0.055;\n  const bLx=CW*0.04,bRx=CW*0.96,bY=CH*0.945;\n\n  // Background\n  ctx.fillStyle=\'#1a4d7a\';ctx.fillRect(0,0,CW,CH);\n\n  // Ground glow\n  const grd=ctx.createRadialGradient(CW/2,CH*0.55,0,CW/2,CH*0.55,CW*0.5);\n  grd.addColorStop(0,\'rgba(120,180,255,0.1)\');grd.addColorStop(1,\'rgba(0,0,0,0)\');\n  ctx.fillStyle=grd;ctx.fillRect(0,0,CW,CH);\n\n  // Glass wall — back (top strip)\n  ctx.beginPath();ctx.moveTo(tLx-CW*0.04,tY-CH*0.045);ctx.lineTo(tRx+CW*0.04,tY-CH*0.045);ctx.lineTo(tRx,tY);ctx.lineTo(tLx,tY);ctx.closePath();\n  ctx.fillStyle=\'rgba(200,230,255,0.14)\';ctx.fill();\n  ctx.strokeStyle=\'rgba(200,230,255,0.5)\';ctx.lineWidth=1.5;ctx.stroke();\n\n  // Glass wall — left side\n  ctx.beginPath();ctx.moveTo(tLx-CW*0.04,tY-CH*0.045);ctx.lineTo(tLx,tY);ctx.lineTo(bLx,bY);ctx.lineTo(bLx-CW*0.04,bY+CH*0.035);ctx.closePath();\n  ctx.fillStyle=\'rgba(200,230,255,0.08)\';ctx.fill();\n  ctx.strokeStyle=\'rgba(200,230,255,0.35)\';ctx.lineWidth=1.2;ctx.stroke();\n\n  // Glass wall — right side\n  ctx.beginPath();ctx.moveTo(tRx+CW*0.04,tY-CH*0.045);ctx.lineTo(tRx,tY);ctx.lineTo(bRx,bY);ctx.lineTo(bRx+CW*0.04,bY+CH*0.035);ctx.closePath();\n  ctx.fillStyle=\'rgba(200,230,255,0.08)\';ctx.fill();\n  ctx.strokeStyle=\'rgba(200,230,255,0.35)\';ctx.lineWidth=1.2;ctx.stroke();\n\n  // Court surface — padel blue\n  ctx.beginPath();ctx.moveTo(tLx,tY);ctx.lineTo(tRx,tY);ctx.lineTo(bRx,bY);ctx.lineTo(bLx,bY);ctx.closePath();\n  ctx.fillStyle=\'#2e6cb0\';ctx.fill();\n\n  // Subtle horizontal lines (floor texture)\n  for(let i=1;i<9;i++){\n    const t=i/9;\n    const lx=tLx+(bLx-tLx)*t,rx=tRx+(bRx-tRx)*t,y=tY+(bY-tY)*t;\n    ctx.beginPath();ctx.moveTo(lx,y);ctx.lineTo(rx,y);\n    ctx.strokeStyle=\'rgba(255,255,255,0.045)\';ctx.lineWidth=0.8;ctx.stroke();\n  }\n\n  // Court boundary — bold white frame (matches official court markings)\n  ctx.beginPath();ctx.moveTo(tLx,tY);ctx.lineTo(tRx,tY);ctx.lineTo(bRx,bY);ctx.lineTo(bLx,bY);ctx.closePath();\n  ctx.strokeStyle=\'rgba(255,255,255,0.92)\';ctx.lineWidth=3;ctx.stroke();\n\n  // Net (at y=0.5)\n  const nL=sc(0,0.5),nR=sc(1,0.5);\n  // Net shadow\n  ctx.beginPath();ctx.moveTo(nL.x,nL.y+3);ctx.lineTo(nR.x,nR.y+3);\n  ctx.strokeStyle=\'rgba(0,0,0,0.35)\';ctx.lineWidth=6;ctx.stroke();\n  // Net surface\n  ctx.beginPath();ctx.moveTo(nL.x,nL.y);ctx.lineTo(nR.x,nR.y);\n  ctx.strokeStyle=\'rgba(255,255,255,0.95)\';ctx.lineWidth=4;ctx.stroke();\n  // Net mesh\n  const nSteps=18;\n  for(let i=0;i<=nSteps;i++){\n    const nx=nL.x+(nR.x-nL.x)*(i/nSteps);\n    const ny=nL.y+(nR.y-nL.y)*(i/nSteps);\n    ctx.beginPath();ctx.moveTo(nx,ny-5);ctx.lineTo(nx,ny+5);\n    ctx.strokeStyle=\'rgba(255,255,255,0.18)\';ctx.lineWidth=0.7;ctx.stroke();\n  }\n  // Net posts\n  const postH=CH*0.04;\n  ctx.fillStyle=\'rgba(230,230,240,0.85)\';\n  ctx.fillRect(nL.x-4,nL.y-postH,6,postH*1.8);\n  ctx.fillRect(nR.x-2,nR.y-postH,6,postH*1.8);\n\n  // Service lines — real padel dimension: 7m from net on a 10m half-court (y=0.5 ± 0.35)\n  const sL1=sc(0,0.15),sR1=sc(1,0.15);\n  const sL2=sc(0,0.85),sR2=sc(1,0.85);\n  ctx.strokeStyle=\'rgba(255,255,255,0.55)\';ctx.lineWidth=2;ctx.setLineDash([]);\n  ctx.beginPath();ctx.moveTo(sL1.x,sL1.y);ctx.lineTo(sR1.x,sR1.y);ctx.stroke();\n  ctx.beginPath();ctx.moveTo(sL2.x,sL2.y);ctx.lineTo(sR2.x,sR2.y);ctx.stroke();\n\n  // Center lines — only within service boxes (between net and service line), matching real court markings\n  const cN=sc(.5,.5),cS1=sc(.5,.15),cS2=sc(.5,.85);\n  ctx.strokeStyle=\'rgba(255,255,255,0.45)\';ctx.lineWidth=1.6;\n  ctx.beginPath();ctx.moveTo(cS1.x,cS1.y);ctx.lineTo(cN.x,cN.y);ctx.stroke();\n  ctx.beginPath();ctx.moveTo(cN.x,cN.y);ctx.lineTo(cS2.x,cS2.y);ctx.stroke();\n\n  // Zone labels\n  ctx.fillStyle=\'rgba(255,255,255,0.1)\';ctx.font=`bold ${Math.round(CW*0.022)}px Inter,sans-serif`;ctx.textAlign=\'center\';\n  const topC=sc(.5,.07);ctx.fillText(\'OPPONENTS\',topC.x,topC.y);\n  const botC=sc(.5,.93);ctx.fillText(\'YOUR TEAM\',botC.x,botC.y);\n\n  // Wall labels\n  ctx.fillStyle=\'rgba(200,230,255,0.4)\';ctx.font=`${Math.round(CW*0.018)}px Inter,sans-serif`;\n  const topMid=sc(.5,.02);ctx.fillText(\'BACK WALL\',topMid.x,topMid.y+2);\n  const botMid=sc(.5,.98);ctx.fillText(\'BACK WALL\',botMid.x,botMid.y-2);\n\n  // NET label\n  ctx.fillStyle=\'rgba(255,255,255,0.35)\';ctx.font=`bold ${Math.round(CW*0.016)}px Inter,sans-serif`;ctx.textAlign=\'left\';\n  ctx.fillText(\'NET\',nR.x+CW*0.02,nR.y+4);\n}\n\nfunction playerSize(ny){\n  // Players further away (small ny = top = far) appear smaller in perspective\n  return Math.round(CW*(0.028+ny*0.022));\n}\n\nfunction drawPlayer(ctx,nx,ny,fill,ring,label,active){\n  const p=sc(nx,ny);\n  const r=playerSize(ny);\n  const bodyH=r*1.6;\n  // Shadow\n  ctx.beginPath();ctx.ellipse(p.x,p.y+r*0.25,r*0.9,r*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=\'rgba(0,0,0,0.45)\';ctx.fill();\n  // Body cylinder (side faces as trapezoid for perspective)\n  ctx.beginPath();\n  ctx.moveTo(p.x-r,p.y);ctx.lineTo(p.x+r,p.y);\n  ctx.lineTo(p.x+r*0.9,p.y-bodyH);ctx.lineTo(p.x-r*0.9,p.y-bodyH);\n  ctx.closePath();\n  ctx.fillStyle=fill;ctx.fill();\n  // Top disc\n  ctx.beginPath();ctx.ellipse(p.x,p.y-bodyH,r*0.9,r*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=ring;ctx.fill();\n  ctx.strokeStyle=ring;ctx.lineWidth=active?2.5:2;ctx.stroke();\n  // Active pulse\n  if(active){\n    ctx.beginPath();ctx.ellipse(p.x,p.y-bodyH,r*1.3,r*0.46,0,0,Math.PI*2);\n    ctx.strokeStyle=\'rgba(62,207,126,0.3)\';ctx.lineWidth=1.5;ctx.stroke();\n    ctx.beginPath();ctx.ellipse(p.x,p.y,r*1.1,r*0.4,0,0,Math.PI*2);\n    ctx.fillStyle=\'rgba(62,207,126,0.06)\';ctx.fill();\n  }\n  // Label on top disc\n  ctx.fillStyle=\'rgba(255,255,255,0.95)\';\n  ctx.font=`bold ${Math.round(r*0.75)}px Inter,sans-serif`;\n  ctx.textAlign=\'center\';ctx.textBaseline=\'middle\';\n  ctx.fillText(label,p.x,p.y-bodyH+r*0.08);\n}\n\nfunction drawArrow(ctx,x1,y1,x2,y2,col){\n  const a=Math.atan2(y2-y1,x2-x1),l=10;\n  ctx.strokeStyle=col;ctx.lineWidth=1.8;ctx.setLineDash([]);\n  ctx.beginPath();ctx.moveTo(x2,y2);\n  ctx.lineTo(x2-l*Math.cos(a-.42),y2-l*Math.sin(a-.42));\n  ctx.moveTo(x2,y2);\n  ctx.lineTo(x2-l*Math.cos(a+.42),y2-l*Math.sin(a+.42));\n  ctx.stroke();\n}\n\nfunction drawBall(ctx,nx,ny,h){\n  const p=sc(nx,ny);\n  const pr=playerSize(ny);\n  const lift=h*CH*0.12;\n  const r=pr*0.45+h*pr*0.35;\n  // Shadow (on court surface — at p.y, not lifted)\n  const sScale=Math.max(0.3,1-h*0.5);\n  ctx.beginPath();ctx.ellipse(p.x,p.y,r*sScale*0.9,r*sScale*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=`rgba(0,0,0,${0.38-h*0.18})`;ctx.fill();\n  // Glow aura when high\n  if(h>0.3){\n    ctx.beginPath();ctx.arc(p.x,p.y-lift,r*2,0,Math.PI*2);\n    ctx.fillStyle=`rgba(212,232,10,${h*0.06})`;ctx.fill();\n  }\n  // Ball body\n  ctx.beginPath();ctx.arc(p.x,p.y-lift,r,0,Math.PI*2);\n  ctx.fillStyle=\'#d4e820\';ctx.fill();\n  ctx.strokeStyle=\'#9aac00\';ctx.lineWidth=1.2;ctx.stroke();\n  // Seam\n  ctx.strokeStyle=\'rgba(255,255,255,0.3)\';ctx.lineWidth=0.9;\n  ctx.beginPath();ctx.arc(p.x,p.y-lift,r,0.3,Math.PI-0.3);ctx.stroke();\n  ctx.beginPath();ctx.arc(p.x,p.y-lift,r,Math.PI+0.3,2*Math.PI-0.3);ctx.stroke();\n  // Highlight\n  ctx.beginPath();ctx.arc(p.x-r*0.28,p.y-lift-r*0.28,r*0.28,0,Math.PI*2);\n  ctx.fillStyle=\'rgba(255,255,255,0.32)\';ctx.fill();\n}\n\nfunction drawTrail(ctx,s,alpha){\n  if(s.h===\'M\')return;\n  const f=sc(s.f.x,s.f.y);\n  const c=s.c?sc(s.c.x,s.c.y):sc((s.f.x+s.t.x)/2,(s.f.y+s.t.y)/2);\n  const t=sc(s.t.x,s.t.y);\n  ctx.beginPath();ctx.moveTo(f.x,f.y);ctx.quadraticCurveTo(c.x,c.y,t.x,t.y);\n  const col=s.h===\'Y\'?`rgba(245,158,11,${alpha})`:`rgba(248,113,113,${alpha})`;\n  ctx.strokeStyle=col;ctx.lineWidth=1.8;ctx.setLineDash([7,5]);ctx.stroke();ctx.setLineDash([]);\n  // Arrowhead\n  const e1=bez(s.f,s.c||{x:(s.f.x+s.t.x)/2,y:(s.f.y+s.t.y)/2},s.t,0.98);\n  const e2=bez(s.f,s.c||{x:(s.f.x+s.t.x)/2,y:(s.f.y+s.t.y)/2},s.t,0.92);\n  const p1=sc(e1.x,e1.y),p2=sc(e2.x,e2.y);\n  drawArrow(ctx,p2.x,p2.y,p1.x,p1.y,col.replace(/[\\d.]+\\)$/,\'0.75)\'));\n}\n\nfunction drawMoveArrows(ctx,s,prevY,curY){\n  if(s.h!==\'M\')return;\n  prevY.forEach((prev,i)=>{\n    const cur=curY[i];\n    if(Math.abs(prev.x-cur.x)<0.01&&Math.abs(prev.y-cur.y)<0.01)return;\n    const f=sc(prev.x,prev.y),t=sc(cur.x,cur.y);\n    ctx.beginPath();ctx.moveTo(f.x,f.y);ctx.lineTo(t.x,t.y);\n    ctx.strokeStyle=\'rgba(167,139,250,0.65)\';ctx.lineWidth=1.8;ctx.setLineDash([5,4]);ctx.stroke();ctx.setLineDash([]);\n    drawArrow(ctx,f.x,f.y,t.x,t.y,\'rgba(167,139,250,0.65)\');\n  });\n}\n\nfunction render(bt){\n  const ctx=canvas.getContext(\'2d\');\n  ctx.clearRect(0,0,CW,CH);\n  const p=getPlay();const shots=p.shots;const et=ease(Math.min(bt??1,1));\n\n  drawCourt(ctx);\n\n  // Past trails\n  for(let i=0;i<shot;i++)drawTrail(ctx,shots[i],0.14);\n  if(shot<shots.length)drawTrail(ctx,shots[shot],0.32);\n\n  // Player positions\n  const s=shots[Math.min(shot,shots.length-1)];\n  const prevY=shot===0?p.sY:(shots[shot-1].yP||p.sY);\n  const prevO=shot===0?p.sO:(shots[shot-1].oP||p.sO);\n  const curY=s.yP||prevY;const curO=s.oP||prevO;\n\n  const py=curY.map((q,i)=>({x:lerp(prevY[i].x,q.x,et),y:lerp(prevY[i].y,q.y,et)}));\n  const po=curO.map((q,i)=>({x:lerp(prevO[i].x,q.x,et),y:lerp(prevO[i].y,q.y,et)}));\n\n  // Move arrows\n  drawMoveArrows(ctx,s,prevY,curY);\n\n  // Draw opponents first (behind net = further = drawn first)\n  po.forEach((q,i)=>drawPlayer(ctx,q.x,q.y,\'#50000e\',\'#dc2626\',[\'O1\',\'O2\'][i],false));\n\n  // Draw your team (in front)\n  py.forEach((q,i)=>drawPlayer(ctx,q.x,q.y,\'#1a0a2e\',i===1?\'#3ecf7e\':\'#7c4de0\',[\'Y1\',\'Y2\'][i],i===1&&s.h===\'M\'));\n\n  // Ball\n  if(shot<shots.length&&s.h!==\'M\'){\n    const f=s.f,c=s.c||{x:(s.f.x+s.t.x)/2,y:(s.f.y+s.t.y)/2},t2=s.t;\n    const bp=bez(f,c,t2,et);\n    const h=(s.ht||0)*Math.sin(et*Math.PI);\n    drawBall(ctx,bp.x,bp.y,h);\n  } else {\n    // Show ball at rest at last position\n    const last=shots[Math.min(shot===shots.length?shot-1:Math.max(shot-1,0),shots.length-1)];\n    if(last)drawBall(ctx,last.t.x,last.t.y,0);\n  }\n\n  // Step badge\n  const total=shots.length;const cur=Math.min(shot+1,total);\n  const badgeText=`Shot ${cur} / ${total}`;\n  ctx.font=`600 ${Math.round(CW*0.018)}px Inter,sans-serif`;\n  const textW=ctx.measureText(badgeText).width;\n  const padX=CW*0.018;\n  const badgeW=textW+padX*2;\n  const badgeH=CH*0.038;\n  const badgeX=CW-badgeW-CW*0.025;\n  const badgeY=CH*0.02;\n  ctx.fillStyle=\'rgba(61,26,110,0.88)\';\n  ctx.beginPath();if(ctx.roundRect)ctx.roundRect(badgeX,badgeY,badgeW,badgeH,badgeH/2);else ctx.rect(badgeX,badgeY,badgeW,badgeH);\n  ctx.fill();\n  ctx.fillStyle=\'rgba(255,255,255,0.9)\';ctx.textAlign=\'center\';\n  ctx.fillText(badgeText,badgeX+badgeW/2,badgeY+badgeH*0.68);\n}\n\n// ── ANIMATION ─────────────────────────────────────────────────────────────────\nfunction animFrame(ts){\n  const s=getShots()[shot];\n  if(!shotStart)shotStart=ts;\n  const t=Math.min((ts-shotStart)/s.d,1);\n  render(t);\n  // Progress\n  const total=getShots().reduce((a,x)=>a+x.d,0);\n  const done=getShots().slice(0,shot).reduce((a,x)=>a+x.d,0)+(ts-shotStart);\n  updateProgress(Math.min(done/total,1));\n  updateShotList(shot);\n  updateShotBar(shot);\n  if(t>=1){\n    shot++;\n    if(shot>=getShots().length){\n      // Done\n      playing=false;\n      document.getElementById(\'playicon\').innerHTML=\'<polygon points="5,3 19,12 5,21"/>\';\n      document.getElementById(\'playbtn\').classList.remove(\'playing\');\n      render(1);updateProgress(1);updateShotList(getShots().length-1);\n      if(autoOn){\n        autoTimer=setTimeout(()=>{\n          shot=0;shotStart=null;\n          if(play<LEVELS[lvl].plays.length-1){play++;loadPlay(play);}\n          else{stopAuto();}\n        },1200);\n      }\n      return;\n    }\n    shotStart=null;\n  }\n  if(playing)animId=requestAnimationFrame(animFrame);\n}\n\nfunction togglePlay(){\n  if(playing){\n    playing=false;if(animId)cancelAnimationFrame(animId);\n    document.getElementById(\'playicon\').innerHTML=\'<polygon points="5,3 19,12 5,21"/>\';\n  } else {\n    if(shot>=getShots().length){shot=0;shotStart=null;updateProgress(0);}\n    playing=true;shotStart=null;\n    document.getElementById(\'playicon\').innerHTML=\'<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>\';\n    document.getElementById(\'playbtn\').classList.add(\'playing\');\n    animId=requestAnimationFrame(animFrame);\n  }\n}\n\nfunction nextShot(){\n  stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);\n  if(shot<getShots().length-1){shot++;render(1);updateShotList(shot);updateShotBar(shot);}\n}\nfunction prevShot(){\n  stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);\n  if(shot>0){shot--;render(1);updateShotList(shot);updateShotBar(shot);}\n}\n\nlet autoOn=false;\nfunction toggleAuto(){\n  if(autoOn){stopAuto();return;}\n  autoOn=true;document.getElementById(\'autobtn\').textContent=\'■ Stop\';\n  shot=0;shotStart=null;updateProgress(0);\n  if(!playing)togglePlay();\n}\nfunction stopAuto(){\n  autoOn=false;document.getElementById(\'autobtn\').textContent=\'▶ Auto\';\n  if(autoTimer){clearTimeout(autoTimer);autoTimer=null;}\n}\n\n// ── UI ────────────────────────────────────────────────────────────────────────\nfunction updateProgress(t){\n  const pct=(t*100).toFixed(1)+\'%\';\n  document.getElementById(\'pfill\').style.width=pct;\n  document.getElementById(\'pthumb\').style.left=`calc(${pct} - 5px)`;\n  const cur=Math.min(shot+1,getShots().length);\n  document.getElementById(\'pmeta\').textContent=`${cur} / ${getShots().length} shots`;\n}\n\nfunction updateShotBar(idx){\n  const s=getShots()[Math.min(idx,getShots().length-1)];\n  if(!s)return;\n  const dot=document.getElementById(\'sdot\');\n  const txt=document.getElementById(\'stxt\');\n  const badge=document.getElementById(\'sbadge\');\n  const col=s.h===\'M\'?\'#a78bfa\':s.h===\'Y\'?\'#f59e0b\':\'#f87171\';\n  dot.style.background=col;\n  txt.textContent=s.l+(s.w?\' ★\':\'\')+(s.e?\' ✗\':\'\');\n  if(s.h===\'M\'){badge.textContent=\'Move\';badge.style.background=\'rgba(167,139,250,.12)\';badge.style.color=\'#a78bfa\';badge.style.border=\'1px solid rgba(167,139,250,.25)\';}\n  else if(s.w){badge.textContent=\'Winner ★\';badge.style.background=\'rgba(245,158,11,.12)\';badge.style.color=\'#f59e0b\';badge.style.border=\'1px solid rgba(245,158,11,.25)\';}\n  else if(s.e){badge.textContent=\'Error ✗\';badge.style.background=\'rgba(248,113,113,.1)\';badge.style.color=\'#f87171\';badge.style.border=\'1px solid rgba(248,113,113,.25)\';}\n  else{badge.textContent=s.h===\'Y\'?\'Your shot\':\'Opp. shot\';badge.style.background=s.h===\'Y\'?\'rgba(245,158,11,.1)\':\'rgba(248,113,113,.08)\';badge.style.color=col;badge.style.border=`1px solid ${col}44`;}\n}\n\nfunction updateShotList(active){\n  const list=document.getElementById(\'rpseq\');\n  list.innerHTML=\'\';\n  const shots=getShots();\n  shots.forEach((s,i)=>{\n    const d=document.createElement(\'div\');\n    d.className=\'seqi\'+(i===active?\' sa\':\'\');\n    d.onclick=()=>{stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);shot=i;render(1);updateShotList(i);updateShotBar(i);};\n    const col=s.h===\'M\'?\'rgba(167,139,250,.12)\':s.h===\'Y\'?\'rgba(245,158,11,.12)\':\'rgba(248,113,113,.1)\';\n    const tcol=s.h===\'M\'?\'#a78bfa\':s.h===\'Y\'?\'#f59e0b\':\'#f87171\';\n    d.innerHTML=`<div class="seqn" style="background:${i===active?tcol:col};color:${i===active?\'#000\':tcol};">${i+1}</div>`+\n      `<div><div class="seqt">${s.l}</div>${s.w?\'<div class="seqw">★ Point won</div>\':\'\'}${s.e?\'<div class="seqe">✗ Error</div>\':\'\'}</div>`;\n    list.appendChild(d);\n  });\n}\n\nfunction buildPlaybar(){\n  const row=document.getElementById(\'pbar\');\n  row.innerHTML=\'\';\n  LEVELS[lvl].plays.forEach((p,i)=>{\n    const d=document.createElement(\'div\');\n    d.className=\'pc\'+(i===play?\' pca\':\'\');\n    d.textContent=`${i+1} · ${p.name}`;\n    d.onclick=()=>loadPlay(i);\n    row.appendChild(d);\n  });\n}\n\nfunction loadPlay(idx){\n  stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);\n  play=idx;shot=0;shotStart=null;\n  document.getElementById(\'playicon\').innerHTML=\'<polygon points="5,3 19,12 5,21"/>\';\n  document.getElementById(\'playbtn\').classList.remove(\'playing\');\n  updateProgress(0);\n  buildPlaybar();\n  const p=getPlay();\n  document.getElementById(\'rpname\').textContent=p.name;\n  document.getElementById(\'lcnt\').textContent=`Play ${idx+1} of ${LEVELS[lvl].plays.length}`;\n  // Tags\n  const tc=p.type===\'Offensive\'?[\'rgba(62,207,126,.1)\',\'#3ecf7e\',\'rgba(62,207,126,.18)\']:p.type===\'Defensive\'?[\'rgba(251,191,36,.08)\',\'#fbbf24\',\'rgba(251,191,36,.2)\']:[\'rgba(147,197,253,.08)\',\'#93c5fd\',\'rgba(147,197,253,.2)\'];\n  const lc=LEVELS[lvl];\n  document.getElementById(\'rptags\').innerHTML=\n    `<span class="rptag" style="background:${tc[0]};color:${tc[1]};border:1px solid ${tc[2]};">${p.type}</span>`+\n    `<span class="rptag" style="background:#f7f5fb;color:${lc.dot};border:1px solid ${lc.dot}55;">${lc.label}</span>`;\n  document.getElementById(\'rpdesc\').textContent=p.desc;\n  document.getElementById(\'fiplvl\').textContent=p.fip;\n  document.getElementById(\'fipt\').textContent=p.fipText;\n  updateShotList(0);updateShotBar(0);\n  render(1);\n}\n\nfunction setLevel(l){\n  stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);\n  lvl=l;play=0;shot=0;shotStart=null;\n  [\'lv0\',\'lv1\',\'lv2\'].forEach((id,i)=>{\n    const el=document.getElementById(id);\n    el.className=\'lv\';\n    if(i===l){el.classList.add(LEVELS[l].cls);el.textContent=LEVELS[l].sym+\' \'+LEVELS[l].label;}\n    else{el.textContent=\'○ \'+LEVELS[i].label;}\n  });\n  buildPlaybar();loadPlay(0);\n}\n\n// INIT\nwindow.addEventListener(\'resize\',()=>{setupCanvas();render(1);});\nrequestAnimationFrame(()=>{\n  setupCanvas();\n  setLevel(0);\n});\n</script>\n\n<div id="libraryModal" style="display:none;position:fixed;inset:0;background:rgba(26,10,46,.45);backdrop-filter:blur(4px);z-index:999;align-items:center;justify-content:center;padding:20px;">\n  <div style="background:#fff;border:1px solid #e2e6ef;border-radius:16px;max-width:520px;width:100%;max-height:80vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(61,26,110,.25);">\n    <div style="padding:18px 20px;border-bottom:1px solid #e2e6ef;display:flex;align-items:center;justify-content:space-between;">\n      <div>\n        <div style="font-size:15px;font-weight:800;color:#1a0a2e;">Padel Plays Library</div>\n        <div style="font-size:11px;color:#9a8aaa;margin-top:2px;">+300 plays &middot; FIP Academy framework</div>\n      </div>\n      <div onclick="closeLibrary()" style="cursor:pointer;color:#9a8aaa;font-size:18px;line-height:1;">✕</div>\n    </div>\n    <div style="padding:14px 20px;border-bottom:1px solid #e2e6ef;">\n      <input type="text" placeholder="Search plays, shots, tactics..." style="width:100%;background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:9px 12px;font-size:12.5px;color:#1a0a2e;outline:none;font-family:inherit;">\n    </div>\n    <div style="padding:16px 20px;overflow-y:auto;">\n      <div style="font-size:11px;font-weight:700;color:#9a8aaa;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">Available now — 18 plays</div>\n      <div style="font-size:12px;color:#5a4a7a;line-height:1.7;margin-bottom:16px;">These are fully animated and ready to demo. Select a level above to explore them.</div>\n      <div style="font-size:11px;font-weight:700;color:#9a8aaa;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">Coming soon — 282 more plays</div>\n      <div style="display:flex;flex-direction:column;gap:6px;">\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Serve plays &middot; 24 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Net domination &middot; 38 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Wall plays &middot; 52 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Defensive plays &middot; 44 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Smash &amp; overhead plays &middot; 36 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Passing shots &middot; 28 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Point construction &middot; 36 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Special &amp; trick plays &middot; 24 more</div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<script>\nfunction openLibrary(){document.getElementById(\'libraryModal\').style.display=\'flex\';}\nfunction closeLibrary(){document.getElementById(\'libraryModal\').style.display=\'none\';}\n\nfunction showToast(msg){\n  const t=document.getElementById(\'ctToast\');\n  if(!t)return;\n  t.textContent=msg;\n  t.style.display=\'block\';\n  setTimeout(()=>t.style.display=\'none\',3500);\n}\nfunction openCreateTactic(){document.getElementById(\'createTacticModal\').classList.add(\'open\');}\nfunction closeCreateTactic(){\n  document.getElementById(\'createTacticModal\').classList.remove(\'open\');\n  resetCtForm();\n}\n\nlet ctVisibility=\'private\';\n\nfunction selectCtVisibility(el){\n  document.querySelectorAll(\'.ct-viz\').forEach(b=>{b.classList.remove(\'sel-private\');b.classList.remove(\'sel-public\');});\n  ctVisibility=el.dataset.viz;\n  if(ctVisibility===\'private\'){\n    el.classList.add(\'sel-private\');\n    document.getElementById(\'ctNotePrivate\').style.display=\'flex\';\n    document.getElementById(\'ctNotePublic\').style.display=\'none\';\n    document.getElementById(\'ctSubmitBtn\').textContent=\'Save private tactic\';\n  } else {\n    el.classList.add(\'sel-public\');\n    document.getElementById(\'ctNotePrivate\').style.display=\'none\';\n    document.getElementById(\'ctNotePublic\').style.display=\'flex\';\n    document.getElementById(\'ctSubmitBtn\').textContent=\'Send for review\';\n  }\n}\n\nfunction selectCtLevel(el){\n  document.querySelectorAll(\'.ct-lv\').forEach(b=>b.classList.remove(\'sel\'));\n  el.classList.add(\'sel\');\n}\n\nfunction resetCtForm(){\n  document.getElementById(\'ctForm\').classList.remove(\'hide\');\n  document.getElementById(\'ctProcessing\').classList.remove(\'show\');\n  document.getElementById(\'ctName\').value=\'\';\n  document.getElementById(\'ctDesc\').value=\'\';\n  document.querySelectorAll(\'.ct-lv\').forEach(b=>b.classList.remove(\'sel\'));\n  document.querySelector(\'.ct-lv[data-lv="intermediate"]\').classList.add(\'sel\');\n  document.querySelectorAll(\'.ct-viz\').forEach(b=>{b.classList.remove(\'sel-private\');b.classList.remove(\'sel-public\');});\n  document.querySelector(\'.ct-viz[data-viz="private"]\').classList.add(\'sel-private\');\n  ctVisibility=\'private\';\n  document.getElementById(\'ctNotePrivate\').style.display=\'flex\';\n  document.getElementById(\'ctNotePublic\').style.display=\'none\';\n  document.getElementById(\'ctSubmitBtn\').textContent=\'Save private tactic\';\n}\n\nfunction submitTactic(){\n  const name=document.getElementById(\'ctName\').value.trim();\n  const desc=document.getElementById(\'ctDesc\').value.trim();\n  if(!name||!desc){\n    showToast(\'Add a tactic name and description before sending\');\n    return;\n  }\n  if(ctVisibility===\'private\'){\n    document.getElementById(\'ctForm\').classList.add(\'hide\');\n    document.getElementById(\'ctProcessing\').classList.add(\'show\');\n    document.getElementById(\'ctProcessing\').querySelector(\'.ct-processing-text\').textContent=\'Saving to your library...\';\n    setTimeout(()=>{\n      closeCreateTactic();\n      showToast(\'Tactic saved — visible to your students now\');\n    },1000);\n  } else {\n    document.getElementById(\'ctForm\').classList.add(\'hide\');\n    document.getElementById(\'ctProcessing\').classList.add(\'show\');\n    document.getElementById(\'ctProcessing\').querySelector(\'.ct-processing-text\').textContent=\'Orbis is interpreting your tactic...\';\n    setTimeout(()=>{\n      closeCreateTactic();\n      showToast(\'Tactic submitted — Orbis will review it and let you know\');\n    },1800);\n  }\n}\n\nlet atSelectedItem=null;\nlet atCurrentStudent={name:\'\',avatar:\'\',session:\'\'};\n\nfunction openAssignTactic(studentName,avatar,session){\n  atCurrentStudent={name:studentName,avatar:avatar,session:session};\n  document.getElementById(\'atStudentName\').textContent=studentName;\n  document.getElementById(\'atAvatar\').textContent=avatar;\n  document.getElementById(\'atSessionInfo\').textContent=\'Next session: \'+session;\n  resetAtForm();\n  document.getElementById(\'assignTacticModal\').classList.add(\'open\');\n}\n\nfunction closeAssignTactic(){\n  document.getElementById(\'assignTacticModal\').classList.remove(\'open\');\n}\n\nfunction resetAtForm(){\n  document.getElementById(\'atSearch\').value=\'\';\n  document.querySelectorAll(\'.at-item\').forEach(i=>i.classList.remove(\'sel\'));\n  document.querySelectorAll(\'.at-tab\').forEach(t=>t.classList.remove(\'sel\'));\n  document.querySelector(\'.at-tab[data-tab="all"]\').classList.add(\'sel\');\n  atSelectedItem=null;\n  filterAtList();\n}\n\nfunction selectAtItem(el){\n  document.querySelectorAll(\'.at-item\').forEach(i=>i.classList.remove(\'sel\'));\n  el.classList.add(\'sel\');\n  atSelectedItem=el.dataset.name;\n}\n\nfunction selectAtTab(el){\n  document.querySelectorAll(\'.at-tab\').forEach(t=>t.classList.remove(\'sel\'));\n  el.classList.add(\'sel\');\n  filterAtList();\n}\n\nfunction filterAtList(){\n  const query=document.getElementById(\'atSearch\').value.trim().toLowerCase();\n  const activeTab=document.querySelector(\'.at-tab.sel\').dataset.tab;\n  const items=document.querySelectorAll(\'.at-item\');\n  let visibleCount=0;\n  items.forEach(item=>{\n    const matchesQuery=!query||item.dataset.name.includes(query);\n    const matchesTab=activeTab===\'all\'||item.dataset.source===activeTab;\n    const show=matchesQuery&&matchesTab;\n    item.style.display=show?\'flex\':\'none\';\n    if(show)visibleCount++;\n  });\n}\n\nfunction submitAssignTactic(){\n  if(!atSelectedItem){\n    showToast(\'Pick a tactic to assign\');\n    return;\n  }\n  closeAssignTactic();\n  showToast(\'Tactic assigned to \'+atCurrentStudent.name+\'\\u2019s next session\');\n}\n</script>\n<div class="ct-overlay" id="createTacticModal">\n  <div class="ct-box">\n    <div class="ct-header">\n      <div>\n        <div class="ct-htitle">Submit a tactic to Orbis</div>\n        <div class="ct-hsub">Describe the rally in your own words — Orbis Core builds the animation</div>\n      </div>\n      <button class="ct-close" onclick="closeCreateTactic()">&#10005;</button>\n    </div>\n    <div class="ct-body">\n\n      <div class="ct-form" id="ctForm">\n        <div class="ct-field">\n          <label class="ct-flabel">Visibility</label>\n          <div class="ct-vizrow">\n            <div class="ct-viz sel-private" data-viz="private" onclick="selectCtVisibility(this)"><i class="ct-viz-icon">&#128274;</i> Private</div>\n            <div class="ct-viz" data-viz="public" onclick="selectCtVisibility(this)"><i class="ct-viz-icon">&#127760;</i> Public</div>\n          </div>\n        </div>\n\n        <div class="ct-field">\n          <label class="ct-flabel">Tactic name</label>\n          <input class="ct-input" id="ctName" placeholder="Cross vibora into the glass after a deep lob">\n        </div>\n\n        <div class="ct-field">\n          <label class="ct-flabel">Level</label>\n          <div class="ct-lvrow">\n            <div class="ct-lv" data-lv="beginner" onclick="selectCtLevel(this)">Beginner</div>\n            <div class="ct-lv sel" data-lv="intermediate" onclick="selectCtLevel(this)">Intermediate</div>\n            <div class="ct-lv" data-lv="advanced" onclick="selectCtLevel(this)">Advanced</div>\n          </div>\n        </div>\n\n        <div class="ct-field">\n          <label class="ct-flabel">Describe the rally</label>\n          <textarea class="ct-textarea" id="ctDesc" placeholder="Serve down the T, both players rush net. Opponent lobs deep cross-court. We let it bounce off the back glass, take it early with a vibora aimed at the side glass on the way down..."></textarea>\n        </div>\n\n        <div class="ct-note ct-note-private" id="ctNotePrivate">\n          <i class="ct-reward-icon">&#128274;</i>\n          <div class="ct-reward-text">Visible only to your students. No Orbis review needed &mdash; saved to your library immediately.</div>\n        </div>\n\n        <div class="ct-note ct-note-public" id="ctNotePublic" style="display:none;">\n          <i class="ct-reward-icon">&#128176;</i>\n          <div class="ct-reward-text">Reviewed by Orbis before publishing. If approved, you earn <b>5 euros for every 1,000 times</b> coaches use this tactic in their sessions.</div>\n        </div>\n\n        <button class="ct-submit" id="ctSubmitBtn" onclick="submitTactic()">Save private tactic</button>\n      </div>\n\n      <div class="ct-processing" id="ctProcessing">\n        <div class="ct-spinner"></div>\n        <div class="ct-processing-text">Orbis is interpreting your tactic...</div>\n      </div>\n\n      <div style="margin-top:24px;">\n        <div class="ct-queue-title">My submitted tactics</div>\n        <div class="ct-qrow">\n          <div>\n            <div class="ct-qname">My fake bandeja drill</div>\n            <div class="ct-qmeta"><i class="ct-qviz-icon">&#128274;</i> Private &middot; saved Jun 28 &middot; used in 3 sessions</div>\n          </div>\n          <div class="ct-qstatus private">Saved</div>\n        </div>\n        <div class="ct-qrow">\n          <div>\n            <div class="ct-qname">Fake bandeja, real chiquita</div>\n            <div class="ct-qmeta"><i class="ct-qviz-icon">&#127760;</i> Public &middot; submitted Jun 24 &middot; 1,240 reproductions</div>\n          </div>\n          <div class="ct-qstatus approved">Approved &mdash; in library</div>\n        </div>\n        <div class="ct-qrow">\n          <div>\n            <div class="ct-qname">Double lob recovery</div>\n            <div class="ct-qmeta"><i class="ct-qviz-icon">&#127760;</i> Public &middot; submitted Jun 20</div>\n          </div>\n          <div class="ct-qstatus revision">Needs revision</div>\n        </div>\n      </div>\n\n    </div>\n  </div>\n</div>\n<div class="at-overlay" id="assignTacticModal">\n  <div class="at-box">\n    <div class="at-header">\n      <div>\n        <div class="at-htitle">Assign a tactic</div>\n        <div class="at-hsub">Choose from your library and link it to this session</div>\n      </div>\n      <button class="at-close" onclick="closeAssignTactic()">&#10005;</button>\n    </div>\n    <div class="at-body">\n\n      <div class="at-student">\n        <div class="at-student-avatar" id="atAvatar">F</div>\n        <div>\n          <div class="at-student-name" id="atStudentName">Fernando de los Rios</div>\n          <div class="at-student-sub" id="atSessionInfo">Next session: Thu 26, 10:00</div>\n        </div>\n      </div>\n\n      <input class="at-search" placeholder="Search tactics..." id="atSearch" oninput="filterAtList()">\n\n      <div class="at-tab-row">\n        <div class="at-tab sel" data-tab="all" onclick="selectAtTab(this)">All</div>\n        <div class="at-tab" data-tab="private" onclick="selectAtTab(this)">My private</div>\n        <div class="at-tab" data-tab="library" onclick="selectAtTab(this)">+300 library</div>\n      </div>\n\n      <div class="at-list" id="atList">\n        <div class="at-item" data-source="private" data-name="my fake bandeja drill" onclick="selectAtItem(this)">\n          <div class="at-icon priv">&#128274;</div>\n          <div class="at-text">\n            <div class="at-name">My fake bandeja drill</div>\n            <div class="at-meta">Private &middot; created by you</div>\n          </div>\n          <div class="at-check">&#10003;</div>\n        </div>\n        <div class="at-item" data-source="library" data-name="bandeja hold at net" onclick="selectAtItem(this)">\n          <div class="at-icon lib">&#127934;</div>\n          <div class="at-text">\n            <div class="at-name">Bandeja hold at net</div>\n            <div class="at-meta">+300 library &middot; Intermediate</div>\n          </div>\n          <div class="at-check">&#10003;</div>\n        </div>\n        <div class="at-item" data-source="library" data-name="serve plus net rush" onclick="selectAtItem(this)">\n          <div class="at-icon lib">&#127934;</div>\n          <div class="at-text">\n            <div class="at-name">Serve + net rush</div>\n            <div class="at-meta">+300 library &middot; Beginner</div>\n          </div>\n          <div class="at-check">&#10003;</div>\n        </div>\n        <div class="at-item" data-source="library" data-name="vibora to side glass" onclick="selectAtItem(this)">\n          <div class="at-icon lib">&#127934;</div>\n          <div class="at-text">\n            <div class="at-name">Vibora to side glass</div>\n            <div class="at-meta">+300 library &middot; Advanced</div>\n          </div>\n          <div class="at-check">&#10003;</div>\n        </div>\n      </div>\n\n      <button class="at-submit" onclick="submitAssignTactic()">Assign to this session</button>\n\n    </div>\n  </div>\n</div>\n</body>\n</html>\n'

@app.get("/demo/simulator", response_class=HTMLResponse)
async def demo_simulator():
    return SIMULATOR_HTML


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
      <div class="session-row"><div class="session-dot"></div><div class="session-date">Jun 20, 2026</div><div class="session-text">Serve and volley drills — 90 min. Recovery 88%. Coach: strong net approach, work on backhand volley placement. <a href="/demo/video" style="color:var(--lime-dark);font-weight:600;font-size:11px;">&#x1F4F9; View backhand analysis &#x2192;</a></div></div>
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


DEMO_VIDEO_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>Orbis AI — Video Analysis</title>\n<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">\n<style>\n:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--green:#16a34a;--amber:#d97706;--red:#dc2626;--radius:10px;--shadow:0 1px 4px rgba(61,26,110,.08),0 4px 16px rgba(61,26,110,.06);}\n*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}\nbody{font-family:\'DM Sans\',sans-serif;background:var(--bg);color:var(--text);font-size:14px;}\n.header{background:var(--navy);height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;box-shadow:0 2px 12px rgba(61,26,110,.25);position:sticky;top:0;z-index:100;}\n.logo{display:flex;align-items:center;gap:10px;}\n.logo-text{font-size:15px;font-weight:700;color:#fff;}.logo-text span{color:var(--lime);}\n.logo-sub{font-size:9px;color:rgba(255,255,255,.4);letter-spacing:.14em;text-transform:uppercase;margin-top:1px;}\n.demo-badge{background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:4px 12px;font-size:11px;color:var(--lime);font-weight:600;}\n.btn-back{background:none;border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.6);border-radius:6px;padding:5px 12px;font-size:11px;cursor:pointer;font-family:inherit;text-decoration:none;}\n.main{max-width:1200px;margin:0 auto;padding:24px 20px 60px;}\n.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;margin-bottom:16px;}\n.card-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}\n.card-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text2);}\n.card-body{padding:16px;}\n.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}\n.metric-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:0.5px solid var(--border);}\n.metric-row:last-child{border-bottom:none;}\n.metric-name{font-size:12px;color:var(--text2);}\n.badge{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;}\n.badge-green{background:var(--lime-pale);color:var(--lime-dark);}\n.badge-amber{background:#fef3c7;color:#92400e;}\n.badge-red{background:#fee2e2;color:#991b1b;}\n.upload-zone{border:1.5px dashed var(--border);border-radius:8px;padding:24px;text-align:center;cursor:pointer;transition:border-color .15s;}\n.upload-zone:hover{border-color:var(--navy);}\n.toast{position:fixed;top:70px;right:20px;background:var(--navy);color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;z-index:999;border-left:3px solid var(--lime);display:none;max-width:280px;line-height:1.5;}\n.student-select{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.25);color:#fff;font-family:inherit;font-size:12px;font-weight:600;border-radius:7px;padding:7px 12px;cursor:pointer;outline:none;}\n.student-select option{background:var(--navy);color:#fff;}\n.score-pill{display:inline-flex;align-items:center;gap:3px;font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;}\n</style>\n</head>\n<body>\n\n<div class="header">\n  <div class="logo">\n    <svg width="28" height="28" viewBox="0 0 64 64" fill="none">\n      <circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/>\n      <circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/>\n      <circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/>\n      <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>\n    </svg>\n    <div>\n      <div class="logo-text">Orbis <span>AI</span></div>\n      <div class="logo-sub">Padel Video Analysis</div>\n    </div>\n  </div>\n  <div style="display:flex;align-items:center;gap:10px;">\n    <span class="demo-badge">Demo mode</span>\n    <a href="/demo/coach" class="btn-back">&#x2190; Coach hub</a>\n  </div>\n</div>\n\n<div class="toast" id="toast"></div>\n\n<div class="main">\n\n  <!-- Header with student selector -->\n  <div style="background:var(--navy);border-radius:var(--radius);padding:20px 24px;margin-bottom:20px;border-left:4px solid var(--lime);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;">\n    <div>\n      <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">\n        <label style="font-size:10px;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.07em;">Student</label>\n        <select class="student-select" id="studentSelect" onchange="showToast(\'Switching analysis — demo shows Fernando only\')">\n          <option value="fernando" selected>Fernando de los Rios</option>\n          <option value="marta">Marta Iglesias</option>\n          <option value="pablo">Pablo Santos</option>\n          <option value="diego">Diego Fernandez</option>\n          <option value="carla">Carla Navarro</option>\n        </select>\n      </div>\n      <div style="font-size:18px;font-weight:700;color:#fff;">Net position &amp; split-step analysis</div>\n      <div style="font-size:13px;color:rgba(255,255,255,.55);margin-top:3px;">Jun 20, 2026 &middot; 0m 48s &middot; Analyzed by Orbis Core</div>\n    </div>\n    <div style="display:flex;align-items:center;gap:10px;">\n      <div style="text-align:center;background:rgba(255,255,255,.08);border-radius:8px;padding:10px 16px;">\n        <div style="font-size:22px;font-weight:700;color:var(--lime);font-family:\'DM Mono\',monospace;">3.5</div>\n        <div style="font-size:10px;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.06em;">Overall</div>\n      </div>\n    </div>\n  </div>\n\n  <div class="grid2">\n\n    <!-- Left: Court snapshot with annotations -->\n    <div>\n      <div class="card">\n        <div class="card-header">\n          <div class="card-title">Session snapshot</div>\n          <span style="font-size:11px;color:var(--text3);">Frame 00:06 &mdash; split-step / ready position</span>\n        </div>\n        <div class="card-body" style="padding:0;position:relative;">\n          <div style="position:relative;display:inline-block;width:100%;">\n            <img src="/static/Padel video.jpg" style="width:100%;display:block;border-radius:0 0 var(--radius) var(--radius);" alt="Fernando padel net position analysis"/>\n            <svg style="position:absolute;top:0;left:0;width:100%;height:100%;" viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg">\n              <rect x="20" y="16" width="110" height="44" rx="8" fill="rgba(61,26,110,0.88)"/>\n              <text x="75" y="34" fill="rgba(255,255,255,0.6)" font-size="11" font-family="sans-serif" text-anchor="middle">TECHNIQUE</text>\n              <text x="75" y="52" fill="#3ecf7e" font-size="18" font-family="sans-serif" font-weight="700" text-anchor="middle">3.5 / 5.0</text>\n              <rect x="830" y="16" width="230" height="32" rx="8" fill="rgba(62,207,126,0.18)" stroke="rgba(62,207,126,0.5)" stroke-width="1.5"/>\n              <text x="945" y="36" fill="#3ecf7e" font-size="13" font-family="sans-serif" font-weight="700" text-anchor="middle">Orbis Core analyzed</text>\n\n              <!-- Knee bend / athletic stance - good -->\n              <circle cx="330" cy="900" r="60" fill="none" stroke="#3ecf7e" stroke-width="3" stroke-dasharray="7 3"/>\n              <line x1="330" y1="840" x2="330" y2="760" stroke="#3ecf7e" stroke-width="2"/>\n              <rect x="200" y="722" width="240" height="34" rx="6" fill="rgba(61,26,110,0.92)"/>\n              <text x="212" y="744" fill="#3ecf7e" font-size="14" font-family="sans-serif" font-weight="700">Good knee bend &#x2713;</text>\n\n              <!-- Paddle ready position - good -->\n              <circle cx="455" cy="800" r="55" fill="none" stroke="#3ecf7e" stroke-width="3" stroke-dasharray="7 3"/>\n              <line x1="500" y1="755" x2="600" y2="690" stroke="#3ecf7e" stroke-width="2"/>\n              <rect x="600" y="660" width="230" height="34" rx="6" fill="rgba(61,26,110,0.92)"/>\n              <text x="612" y="682" fill="#3ecf7e" font-size="14" font-family="sans-serif" font-weight="700">Paddle low &amp; ready &#x2713;</text>\n\n              <!-- Split-step timing - amber -->\n              <circle cx="320" cy="950" r="50" fill="none" stroke="#f59e0b" stroke-width="3" stroke-dasharray="8 4"/>\n              <line x1="280" y1="965" x2="180" y2="1010" stroke="#f59e0b" stroke-width="2"/>\n              <rect x="40" y="995" width="220" height="34" rx="6" fill="rgba(61,26,110,0.92)"/>\n              <text x="52" y="1017" fill="#f59e0b" font-size="14" font-family="sans-serif" font-weight="700">&#x26A0; Split-step late</text>\n\n              <!-- Weight distribution - red -->\n              <circle cx="300" cy="700" r="48" fill="none" stroke="#dc2626" stroke-width="3" stroke-dasharray="6 3"/>\n              <line x1="260" y1="680" x2="150" y2="630" stroke="#dc2626" stroke-width="2"/>\n              <rect x="20" y="600" width="220" height="34" rx="6" fill="rgba(61,26,110,0.92)"/>\n              <text x="32" y="622" fill="#dc2626" font-size="14" font-family="sans-serif" font-weight="700">&#x2717; Weight too far back</text>\n\n              <!-- Net positioning depth - good -->\n              <circle cx="340" cy="1010" r="42" fill="none" stroke="#3ecf7e" stroke-width="3" stroke-dasharray="7 3"/>\n              <line x1="380" y1="1010" x2="480" y2="1010" stroke="#3ecf7e" stroke-width="2"/>\n              <rect x="480" y="993" width="220" height="34" rx="6" fill="rgba(61,26,110,0.92)"/>\n              <text x="492" y="1015" fill="#3ecf7e" font-size="14" font-family="sans-serif" font-weight="700">Net depth (3m line) &#x2713;</text>\n\n              <rect x="20" y="1024" width="100" height="26" rx="5" fill="rgba(0,0,0,0.65)"/>\n              <text x="70" y="1041" fill="#fff" font-size="12" font-family="monospace" text-anchor="middle">00:06 / 00:48</text>\n              <rect x="940" y="1024" width="120" height="26" rx="5" fill="rgba(61,26,110,0.8)"/>\n              <text x="1000" y="1041" fill="#3ecf7e" font-size="11" font-family="sans-serif" text-anchor="middle">Jun 20, 2026</text>\n            </svg>\n          </div>\n        </div>\n      </div>\n\n      <!-- Upload new video -->\n      <div class="card">\n        <div class="card-header">\n          <div class="card-title">Upload new video</div>\n        </div>\n        <div class="card-body">\n          <div class="upload-zone" onclick="showToast(\'Video upload — processing coming soon\')">\n            <div style="font-size:28px;margin-bottom:8px;">&#x1F3D3;</div>\n            <div style="font-size:13px;font-weight:500;color:var(--text2);">Drop video here or click to upload</div>\n            <div style="font-size:11px;color:var(--text3);margin-top:4px;">MP4 &middot; MOV &middot; max 500MB</div>\n            <div style="margin-top:12px;background:var(--navy);color:#fff;font-size:12px;font-weight:600;padding:8px 20px;border-radius:7px;display:inline-block;">Analyze with Orbis Core</div>\n          </div>\n        </div>\n      </div>\n    </div>\n\n    <!-- Right: Full analysis -->\n    <div>\n\n      <!-- Key finding -->\n      <div class="card">\n        <div class="card-header">\n          <div class="card-title">Key finding</div>\n          <span style="background:rgba(62,207,126,.12);border:1px solid rgba(62,207,126,.25);border-radius:20px;padding:2px 8px;font-size:10px;color:var(--lime-dark);font-weight:600;">Orbis Core</span>\n        </div>\n        <div class="card-body">\n          <div style="background:var(--navy);border-radius:8px;padding:14px 16px;border-left:3px solid var(--lime);">\n            <div style="font-size:13px;color:#fff;line-height:1.6;">Fernando\'s split-step is <strong style="color:var(--lime);">consistently 80-120ms late</strong> relative to his opponent\'s contact, leaving his weight back on his heels when the ball arrives at net. This delays his first move on volleys and chiquitas.</div>\n          </div>\n          <div style="margin-top:10px;background:#fef3c7;border-radius:8px;padding:10px 12px;border-left:3px solid var(--amber);">\n            <div style="font-size:11px;font-weight:700;color:#92400e;margin-bottom:3px;">Impact on net play</div>\n            <div style="font-size:12px;color:#78350f;line-height:1.5;">Late split-step is the root cause behind 3 of his last 5 lost net exchanges. Fixing timing alone should improve his first-volley reaction by roughly 0.15-0.2s.</div>\n          </div>\n        </div>\n      </div>\n\n      <!-- Technique breakdown — Padel AI-style six categories -->\n      <div class="card">\n        <div class="card-header">\n          <div class="card-title">Technique breakdown</div>\n          <span style="font-size:11px;color:var(--text3);">6 padel-specific categories</span>\n        </div>\n        <div class="card-body">\n          <div class="metric-row">\n            <span class="metric-name">Paddle ready position</span>\n            <span class="badge badge-green">&#x2713; Good</span>\n          </div>\n          <div class="metric-row">\n            <span class="metric-name">Knee bend / athletic stance</span>\n            <span class="badge badge-green">&#x2713; Good</span>\n          </div>\n          <div class="metric-row">\n            <span class="metric-name">Net positioning depth</span>\n            <span class="badge badge-green">&#x2713; Good</span>\n          </div>\n          <div class="metric-row">\n            <span class="metric-name">Split-step timing</span>\n            <span class="badge badge-amber">&#x26A0; Late &mdash; 80-120ms</span>\n          </div>\n          <div class="metric-row">\n            <span class="metric-name">Weight distribution</span>\n            <span class="badge badge-red">&#x2717; Back on heels</span>\n          </div>\n          <div class="metric-row">\n            <span class="metric-name">First-move reaction</span>\n            <span class="badge badge-amber">&#x26A0; Below potential</span>\n          </div>\n        </div>\n      </div>\n\n      <!-- FIP drill recommendation -->\n      <div class="card">\n        <div class="card-header">\n          <div class="card-title">Drill recommendation</div>\n          <span style="font-size:11px;color:var(--text3);">FIP Academy Level 1 framework</span>\n        </div>\n        <div class="card-body">\n          <div style="display:flex;flex-direction:column;gap:10px;">\n            <div style="background:var(--lime-pale);border-radius:8px;padding:12px 14px;border-left:3px solid var(--lime-dark);">\n              <div style="font-size:11px;font-weight:700;color:var(--lime-dark);margin-bottom:4px;">Drill 1 &mdash; Split-step timing ladder</div>\n              <div style="font-size:12px;color:var(--text);line-height:1.5;">Coach feeds balls from baseline at random intervals. Fernando must split-step the instant the coach\'s paddle touches the ball, not after. 3 sets of 15 reps, weight forward onto the balls of the feet.</div>\n            </div>\n            <div style="background:var(--bg);border-radius:8px;padding:12px 14px;border-left:3px solid var(--navy);">\n              <div style="font-size:11px;font-weight:700;color:var(--navy);margin-bottom:4px;">Drill 2 &mdash; Forward weight shadow volleys</div>\n              <div style="font-size:12px;color:var(--text);line-height:1.5;">Shadow volleys without a ball, exaggerating a forward weight transfer through contact. 20 reps each side. FIP Academy Level 1 &mdash; net fundamentals progression.</div>\n            </div>\n            <div style="background:var(--bg);border-radius:8px;padding:12px 14px;border-left:3px solid var(--navy);">\n              <div style="font-size:11px;font-weight:700;color:var(--navy);margin-bottom:4px;">Drill 3 &mdash; Reaction volley pairs</div>\n              <div style="font-size:12px;color:var(--text);line-height:1.5;">Partner feeds fast volleys at random angles from 3m. Fernando reacts off the split-step only &mdash; no anticipation. 15 min, builds first-move speed under real net pressure.</div>\n            </div>\n          </div>\n        </div>\n      </div>\n\n      <!-- Coach note -->\n      <div style="background:var(--navy);border-radius:var(--radius);padding:16px 20px;border-left:4px solid var(--lime);">\n        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--lime);margin-bottom:6px;">Orbis Core &mdash; Coach recommendation</div>\n        <div style="font-size:13px;color:rgba(255,255,255,.85);line-height:1.6;">Thursday session (84% recovery &mdash; green light): Start with 10min split-step ladder, then 15min reaction volley pairs. Fernando\'s net win rate should improve noticeably once split-step timing and forward weight transfer are corrected together &mdash; they\'re directly linked.</div>\n      </div>\n\n    </div>\n  </div>\n</div>\n\n<script>\nfunction showToast(msg){const t=document.getElementById(\'toast\');t.textContent=msg;t.style.display=\'block\';setTimeout(()=>t.style.display=\'none\',3000);}\n</script>\n</body>\n</html>'
@app.get("/demo/video", response_class=HTMLResponse)
async def demo_video():
    return DEMO_VIDEO_HTML


@app.post("/api/waitlist")
async def join_waitlist(request: Request):
    body = await request.json()
    sb = get_supabase()
    try:
        sb.table("waitlist").insert({
            "name": body.get("name",""),
            "email": body.get("email",""),
            "country": body.get("country",""),
            "city": body.get("city",""),
            "sport": body.get("sport","tennis"),
        }).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/waitlist", response_class=HTMLResponse)
async def waitlist_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbis AI — Join Waiting List</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
:root{--navy:#3d1a6e;--lime:#3ecf7e;--lime-dark:#2aad62;--lime-pale:#d4f5e5;--bg:#f2f0f7;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--border:#e2e6ef;}
body{font-family:'DM Sans',sans-serif;background:linear-gradient(160deg,#2a0f52 0%,#3d1a6e 50%,#1a0a2e 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;}
.card{background:#fff;border-radius:20px;padding:44px;max-width:440px;width:100%;box-shadow:0 24px 64px rgba(0,0,0,.25);}
.logo{display:flex;align-items:center;gap:8px;margin-bottom:28px;}
.logo-text{font-size:16px;font-weight:800;color:var(--navy);}
.logo-text span{color:var(--lime-dark);}
h2{font-size:24px;font-weight:800;color:var(--text);letter-spacing:-.02em;margin-bottom:6px;}
.sub{font-size:14px;color:var(--text2);margin-bottom:28px;line-height:1.6;}
.field{margin-bottom:16px;}
label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text3);margin-bottom:6px;}
input,select{width:100%;border:1.5px solid var(--border);border-radius:8px;padding:11px 14px;font-size:14px;font-family:inherit;color:var(--text);outline:none;transition:border .15s;background:#fff;}
input:focus,select:focus{border-color:var(--navy);}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.btn{width:100%;background:var(--navy);color:#fff;border:none;border-radius:8px;padding:13px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:6px;transition:background .2s;}
.btn:hover{background:#4a2080;}
.btn:disabled{opacity:.5;cursor:not-allowed;}
.back{display:block;text-align:center;margin-top:16px;font-size:13px;color:var(--text3);text-decoration:none;}
.back:hover{color:var(--navy);}
.success{display:none;text-align:center;padding:20px 0;}
.check{width:60px;height:60px;background:var(--lime-pale);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:28px;}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <svg width="24" height="24" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/><path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/></svg>
    <div class="logo-text">Orbis <span>AI</span></div>
  </div>

  <div id="formSection">
    <h2>Join the waiting list</h2>
    <p class="sub">Be among the first tennis and padel coaches to get access. We are onboarding coaches across Europe and LatAm.</p>
    <div class="field"><label>Full name</label><input type="text" id="wl-name" placeholder="Toni Alcala"></div>
    <div class="field"><label>Email</label><input type="email" id="wl-email" placeholder="toni@academy.com"></div>
    <div class="row2">
      <div class="field"><label>Country</label><input type="text" id="wl-country" placeholder="Spain"></div>
      <div class="field"><label>City</label><input type="text" id="wl-city" placeholder="Madrid"></div>
    </div>
    <div class="field">
      <label>Sport</label>
      <select id="wl-sport">
        <option value="tennis">Tennis</option>
        <option value="padel">Padel</option>
        <option value="both">Both tennis and padel</option>
      </select>
    </div>
    <button class="btn" id="wl-btn" onclick="submitWaitlist()">Join waiting list &rarr;</button>
    <a href="/" class="back">&larr; Back to home</a>
  </div>

  <div class="success" id="successSection">
    <div class="check">&#x2705;</div>
    <h2 style="margin-bottom:8px;">You are on the list!</h2>
    <p style="font-size:14px;color:#5a4a7a;line-height:1.6;margin-bottom:20px;">We will reach out as soon as early access opens in your region. Thank you for joining Orbis AI.</p>
    <a href="/" class="back">&larr; Back to home</a>
  </div>
</div>

<script>
async function submitWaitlist() {
  var name = document.getElementById('wl-name').value.trim();
  var email = document.getElementById('wl-email').value.trim();
  var country = document.getElementById('wl-country').value.trim();
  var city = document.getElementById('wl-city').value.trim();
  var sport = document.getElementById('wl-sport').value;
  if (!name || !email) { alert('Please enter your name and email.'); return; }
  var btn = document.getElementById('wl-btn');
  btn.disabled = true;
  btn.textContent = 'Saving...';
  try {
    var res = await fetch('/api/waitlist', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name: name, email: email, country: country, city: city, sport: sport})
    });
    if (res.ok) {
      document.getElementById('formSection').style.display = 'none';
      document.getElementById('successSection').style.display = 'block';
    } else {
      btn.disabled = false;
      btn.textContent = 'Join waiting list';
      alert('Something went wrong. Please try again.');
    }
  } catch(e) {
    btn.disabled = false;
    btn.textContent = 'Join waiting list';
    alert('Network error. Please try again.');
  }
}
</script>
</body>
</html>"""



@app.get("/demo/player", response_class=HTMLResponse)
async def demo_player():
    return HTMLResponse(content='<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">\n<title>Orbis AI — Train</title>\n<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n<style>\n:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-pale:#d4f5e5;--lime-dark:#2aad62;--bg:#f2f0f7;--surface:#fff;--border:#e2e6ef;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--amber:#ffb84d;--purple:#7c4de0;}\n*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}\nhtml,body{height:100%;background:var(--bg);font-family:\'Inter\',system-ui,sans-serif;color:var(--text);overscroll-behavior:none;}\n.app-shell{max-width:420px;margin:0 auto;min-height:100vh;background:var(--surface);display:flex;flex-direction:column;position:relative;box-shadow:0 0 40px rgba(61,26,110,.08);padding-bottom:64px;}\n\n.top{background:var(--navy);padding:16px 18px 14px;color:#fff;flex-shrink:0;}\n.top-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;}\n.greeting{font-size:14px;font-weight:700;}\n.greeting span{color:var(--lime);}\n.streak{display:flex;align-items:center;gap:5px;background:rgba(255,159,28,.18);border:1px solid rgba(255,159,28,.4);border-radius:20px;padding:4px 10px;font-size:11.5px;font-weight:700;color:var(--amber);}\n.icon-xs{width:12px;height:12px;flex-shrink:0;}\n.icon-sm{width:16px;height:16px;flex-shrink:0;}\n\n.xp-total-row{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.08);border-radius:10px;padding:10px 12px;margin-bottom:10px;}\n.xp-total-card{flex-shrink:0;text-align:center;}\n.xp-total-label{font-size:8.5px;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.04em;}\n.xp-total-val{font-size:18px;font-weight:800;color:var(--lime);}\n.xp-total-next{flex:1;}\n.xp-total-next-label{font-size:8.5px;color:rgba(255,255,255,.4);}\n.xp-total-next-val{font-size:10.5px;font-weight:700;color:#fff;margin-bottom:4px;}\n.xp-total-track{height:5px;background:rgba(255,255,255,.15);border-radius:3px;overflow:hidden;}\n.xp-total-fill{height:100%;background:var(--lime);border-radius:3px;}\n.xp-row{display:flex;gap:8px;}\n.xp-card{flex:1;background:rgba(255,255,255,.08);border-radius:10px;padding:8px 9px;}\n.xp-label{display:flex;align-items:center;gap:4px;font-size:8.5px;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px;}\n.xp-label i{font-size:10px;}\n.xp-bar-track{height:5px;background:rgba(255,255,255,.15);border-radius:3px;overflow:hidden;margin-top:5px;}\n.xp-bar-fill{height:100%;border-radius:3px;transition:width .3s;}\n.xp-val{font-size:10.5px;font-weight:700;color:#fff;}\n\n.screen{display:none;padding-bottom:24px;}\n.screen.active{display:block;}\n\n.section-title{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:700;color:var(--text);margin:0 0 12px;padding:0 18px;}\n.section-title i{font-size:15px;color:var(--purple);}\n.section-title:first-child{margin-top:18px;}\n\n.bottom-nav{position:fixed;bottom:0;left:0;right:0;display:flex;border-top:0.5px solid var(--border);background:#fff;flex-shrink:0;z-index:20;max-width:420px;}\n.nav-item{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;padding:10px 0;font-size:9px;color:var(--text3);font-weight:600;cursor:pointer;background:none;border:none;font-family:inherit;}\n.nav-item.active{color:var(--navy);}\n.nav-icon{width:18px;height:18px;}\n\n.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:var(--navy);color:#fff;padding:11px 20px;border-radius:9px;font-size:12.5px;font-weight:600;z-index:9999;display:none;box-shadow:0 8px 24px rgba(0,0,0,.2);white-space:nowrap;max-width:90%;text-align:center;}\n.quiz-card{background:linear-gradient(135deg,#1a5c38 0%,#0d2818 100%);border-radius:16px;padding:18px;position:relative;overflow:hidden;cursor:pointer;}\n.quiz-badge{display:inline-flex;align-items:center;gap:5px;background:rgba(62,207,126,.18);border:1px solid rgba(62,207,126,.35);border-radius:20px;padding:3px 9px;font-size:9.5px;font-weight:700;color:var(--lime);margin-bottom:10px;}\n.qb-icon{font-size:12px;}\n.quiz-title{font-size:14.5px;font-weight:700;color:#fff;margin-bottom:5px;}\n.quiz-sub{font-size:11px;color:rgba(255,255,255,.55);margin-bottom:14px;}\n.quiz-btn{background:var(--lime);color:#0a2a16;font-size:12.5px;font-weight:700;padding:9px 16px;border-radius:9px;display:inline-flex;align-items:center;gap:6px;}\n.qbtn-icon{font-size:12px;}\n\n.streak-cal{display:flex;gap:6px;}\n.day{flex:1;aspect-ratio:1;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;}\n.day.done{background:var(--lime-pale);color:var(--lime-dark);}\n.day.today{background:var(--navy);color:#fff;}\n.day.future{background:#f0eef8;color:#c4bedb;}\n\n.tree{position:relative;}\n.tree-row{display:flex;align-items:center;gap:0;position:relative;margin-bottom:4px;}\n.tree-node{width:50px;height:50px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;border:3px solid transparent;position:relative;z-index:2;}\n.tn-icon{font-size:18px;}\n.tree-node.done{background:var(--lime-pale);border-color:var(--lime);color:var(--lime-dark);}\n.tree-node.active{background:var(--navy);border-color:var(--purple);color:#fff;box-shadow:0 0 0 4px rgba(124,77,224,.18);}\n.tree-node.locked{background:#f0eef8;border-color:var(--border);color:#c4bedb;}\n.tree-line{flex:1;height:3px;background:var(--border);margin:0 -2px;}\n.tree-line.done{background:var(--lime);}\n.tree-meta{display:flex;justify-content:space-between;font-size:9px;color:var(--text3);padding:0 2px;margin-top:4px;}\n\n.play-row{display:flex;align-items:center;gap:11px;background:#f7f5fb;border-radius:11px;padding:10px 12px;cursor:pointer;}\n.play-list-wrap{padding:0 18px;display:flex;flex-direction:column;gap:8px;}\n.play-icon{width:34px;height:34px;border-radius:9px;background:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;border:1px solid var(--border);}\n.play-name{font-size:12.5px;font-weight:700;color:var(--text);}\n.play-meta{display:flex;align-items:center;gap:4px;font-size:10px;color:var(--text3);margin-top:1px;}\n.pm-icon{font-size:11px;}\n.play-check{margin-left:auto;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;}\n.play-check.done{background:var(--lime-pale);color:var(--lime-dark);}\n.play-check.todo{background:#fff;border:1.5px solid var(--border);}\n.pc-icon{font-size:11px;}\n\n.search-box{position:relative;}\n.search-icon-svg{position:absolute;left:11px;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--text3);}\n.search-box input{width:100%;border:1px solid var(--border);border-radius:9px;padding:9px 12px 9px 32px;font-size:12.5px;font-family:inherit;outline:none;}\n.search-box input:focus{border-color:var(--navy);}\n\n.filter-row{display:flex;gap:6px;overflow-x:auto;}\n.filter-chip{padding:6px 12px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid var(--border);background:#fff;color:var(--text2);cursor:pointer;white-space:nowrap;flex-shrink:0;}\n.filter-chip.active{background:var(--navy);color:#fff;border-color:var(--navy);}\n\n.empty-state,.empty-hint{text-align:center;padding:30px 24px;font-size:12px;color:var(--text3);}\n\n.watch-top{background:var(--navy);height:44px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;}\n.watch-back{color:rgba(255,255,255,.7);width:16px;height:16px;cursor:pointer;}\n.watch-title{font-size:12.5px;font-weight:700;color:#fff;}\n.xp-pill{display:flex;align-items:center;gap:4px;background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:3px 8px;font-size:10px;font-weight:700;color:var(--lime);}\n.xpp-icon{font-size:11px;}\n\n.watch-court{background:#1a4d7a;height:220px;position:relative;overflow:hidden;}\n#watchCanvas{display:block;width:100%;height:100%;}\n.watch-progress{position:absolute;bottom:0;left:0;right:0;height:3px;background:rgba(255,255,255,.15);}\n.watch-progress-fill{height:100%;background:var(--lime);width:0%;transition:width .1s linear;}\n\n.step-label{display:flex;align-items:center;gap:7px;font-size:11px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;}\n.step-icon{font-size:13px;}\n.locked-card{background:#f7f5fb;border:1.5px dashed #d4cfe8;border-radius:12px;padding:16px;text-align:center;}\n.locked-icon{width:38px;height:38px;border-radius:50%;background:#fff;border:1px solid var(--border);display:flex;align-items:center;justify-content:center;margin:0 auto 10px;font-size:17px;color:var(--text3);}\n.li-icon{font-size:17px;}\n.locked-title{font-size:12.5px;font-weight:700;color:var(--text);margin-bottom:4px;}\n.locked-sub{font-size:11px;color:var(--text3);line-height:1.5;}\n.watch-cta-btn{margin-top:12px;background:var(--lime);color:#0a2a16;font-size:12.5px;font-weight:700;padding:10px;border-radius:9px;cursor:pointer;}\n.zero-note{display:flex;align-items:center;gap:6px;font-size:10.5px;color:#c4915c;background:#fff7ed;border:1px solid #fde4c4;border-radius:8px;padding:9px 11px;margin-top:14px;}\n.zn-icon{font-size:14px;flex-shrink:0;}\n\n.quiz-frame{background:var(--text);padding:20px 18px;min-height:240px;display:flex;flex-direction:column;}\n.quiz-q{font-size:14px;font-weight:700;color:#fff;margin-bottom:16px;line-height:1.45;}\n.quiz-opt{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:12px 14px;font-size:12.5px;color:rgba(255,255,255,.8);margin-bottom:9px;cursor:pointer;}\n.quiz-opt.correct-sel{background:rgba(62,207,126,.18);border-color:var(--lime);color:var(--lime);font-weight:700;}\n.quiz-opt.wrong-sel{background:rgba(248,113,113,.12);border-color:#f87171;color:#f87171;}\n.quiz-reward{margin-top:auto;display:flex;align-items:center;justify-content:center;gap:7px;background:rgba(62,207,126,.12);border:1px solid rgba(62,207,126,.3);border-radius:10px;padding:11px;font-size:12.5px;font-weight:700;color:var(--lime);}\n\n.loc-found{background:linear-gradient(135deg,#1a5c38 0%,#0d2818 100%);border-radius:14px;padding:18px;text-align:center;}\n.loc-pin{width:42px;height:42px;border-radius:50%;background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.35);display:flex;align-items:center;justify-content:center;margin:0 auto 12px;font-size:19px;color:var(--lime);}\n.lp-icon{font-size:19px;}\n.loc-title{font-size:13px;font-weight:700;color:#fff;margin-bottom:5px;}\n.loc-club{font-size:11.5px;color:var(--lime);font-weight:600;margin-bottom:4px;}\n.loc-sub{font-size:10.5px;color:rgba(255,255,255,.5);line-height:1.5;margin-bottom:14px;}\n\n.tier-list{display:flex;flex-direction:column;gap:8px;text-align:left;}\n.tier-card{position:relative;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:11px;padding:11px 13px;display:flex;align-items:center;gap:10px;cursor:pointer;}\n.tier-card.recommended{border-color:var(--purple);background:rgba(124,77,224,.12);}\n.tier-badge{position:absolute;top:-7px;right:10px;background:var(--purple);color:#fff;font-size:8px;font-weight:700;padding:2px 7px;border-radius:20px;text-transform:uppercase;letter-spacing:.04em;}\n.tier-icon{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;}\n.ti-icon{font-size:14px;}\n.tier-icon.loc{background:rgba(62,207,126,.15);color:var(--lime);}\n.tier-icon.coach{background:rgba(124,77,224,.2);color:#a78bfa;}\n.tier-text{flex:1;}\n.tier-name{font-size:11.5px;font-weight:700;color:#fff;}\n.tier-desc{font-size:9.5px;color:rgba(255,255,255,.45);margin-top:1px;}\n.tier-xp{font-size:12px;font-weight:800;color:var(--lime);white-space:nowrap;}\n.tier-card.skip{border-color:rgba(255,255,255,.1);background:rgba(255,255,255,.03);}\n.tier-icon.skip-icon{background:rgba(255,255,255,.08);color:rgba(255,255,255,.4);}\n.tier-card.skip .tier-name{color:rgba(255,255,255,.55);}\n.tier-card.skip .tier-desc{color:rgba(255,255,255,.3);}\n.tier-xp.skip-xp{color:rgba(255,255,255,.35);font-size:10.5px;font-weight:600;}\n\n.quiz-pro-tag{display:inline-flex;align-items:center;background:rgba(124,77,224,.15);border:1px solid rgba(124,77,224,.3);border-radius:20px;padding:4px 11px;font-size:10px;font-weight:700;color:#a78bfa;margin-bottom:14px;}\n.quiz-pro-tag.news-tag{background:rgba(62,207,126,.15);border-color:rgba(62,207,126,.3);color:var(--lime);}\n\n.quiz-lock-card{text-align:center;padding:30px 16px;margin-top:auto;margin-bottom:auto;}\n.quiz-lock-icon{width:46px;height:46px;border-radius:50%;background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.3);display:flex;align-items:center;justify-content:center;margin:0 auto 14px;color:#f87171;}\n.quiz-lock-text{font-size:12px;color:rgba(255,255,255,.5);margin-bottom:6px;}\n.quiz-lock-timer{font-size:28px;font-weight:800;color:#fff;font-variant-numeric:tabular-nums;}\n\n.quiz-result-card{text-align:center;padding:30px 16px;margin-top:auto;margin-bottom:auto;}\n.quiz-result-icon{width:46px;height:46px;border-radius:50%;background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.35);display:flex;align-items:center;justify-content:center;margin:0 auto 14px;color:var(--lime);}\n.quiz-result-title{font-size:14px;font-weight:700;color:#fff;margin-bottom:6px;}\n.quiz-result-xp{font-size:20px;font-weight:800;color:var(--lime);margin-bottom:18px;}\n.quiz-result-btn{background:var(--lime);color:#0a2a16;font-size:12.5px;font-weight:700;padding:10px 22px;border-radius:9px;display:inline-block;cursor:pointer;}\n\n.coach-pending{background:#fff;border:1px solid var(--border);border-radius:14px;padding:18px;text-align:center;}\n.coach-avatar{width:46px;height:46px;border-radius:50%;background:var(--lime-pale);border:2px solid var(--lime);display:flex;align-items:center;justify-content:center;margin:0 auto 12px;font-size:18px;font-weight:700;color:var(--lime-dark);}\n.coach-title{font-size:13px;font-weight:700;color:var(--text);margin-bottom:5px;}\n.coach-sub{font-size:11px;color:var(--text3);line-height:1.55;margin-bottom:12px;}\n.coach-status{display:inline-flex;align-items:center;gap:6px;background:#fef3c7;border:1px solid #fcd989;border-radius:20px;padding:5px 12px;font-size:10.5px;font-weight:700;color:#92400e;}\n.cs-icon{font-size:12px;}\n.fallback-note{margin-top:14px;font-size:11px;color:var(--text3);text-decoration:underline;cursor:pointer;}\n\n.profile-card{text-align:center;margin-bottom:20px;}\n.profile-avatar{width:64px;height:64px;border-radius:50%;background:var(--lime-pale);border:2px solid var(--lime);display:flex;align-items:center;justify-content:center;margin:0 auto 12px;font-size:24px;font-weight:700;color:var(--lime-dark);}\n.profile-name{font-size:15px;font-weight:700;color:var(--text);}\n.profile-sub{font-size:11px;color:var(--text3);margin-top:2px;}\n.profile-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:24px;}\n.profile-stat{background:#f7f5fb;border-radius:11px;padding:14px 8px;text-align:center;}\n.profile-stat-val{font-size:18px;font-weight:800;color:var(--navy);}\n.profile-stat-label{font-size:9.5px;color:var(--text3);margin-top:3px;text-transform:uppercase;letter-spacing:.04em;}\n.profile-section-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text3);margin-bottom:10px;}\n.profile-coach-card{display:flex;align-items:center;gap:11px;background:#f7f5fb;border-radius:11px;padding:12px 14px;}\n.profile-coach-avatar{width:36px;height:36px;border-radius:50%;background:var(--lime-pale);color:var(--lime-dark);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;}\n.profile-coach-name{font-size:12.5px;font-weight:700;color:var(--text);}\n.profile-coach-sub{font-size:10.5px;color:var(--text3);margin-top:1px;}\n\n</style>\n</head>\n<body>\n<div class="app-shell" id="appShell">\n\n  <div class="toast" id="toast"></div>\n\n    <div class="top">\n    <div class="top-row">\n      <div class="greeting">Hey, <span>Carlos</span></div>\n      <div class="streak">\n        <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 11-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 002.5 2.5z"/></svg>\n        <span id="streakCount">12</span> day streak\n      </div>\n    </div>\n    <div class="xp-total-row">\n      <div class="xp-total-card">\n        <div class="xp-total-label">Total XP</div>\n        <div class="xp-total-val" id="totalXpVal">840</div>\n      </div>\n      <div class="xp-total-next">\n        <div class="xp-total-next-label">Next reward at</div>\n        <div class="xp-total-next-val">1,000 XP</div>\n        <div class="xp-total-track"><div class="xp-total-fill" id="xpTotalFill" style="width:84%;"></div></div>\n      </div>\n    </div>\n    <div class="xp-row">\n      <div class="xp-card">\n        <div class="xp-label">\n          <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>\n          Net play\n        </div>\n        <div class="xp-val">Level 4</div>\n        <div class="xp-bar-track"><div class="xp-bar-fill" id="xpNet" style="width:70%;background:var(--lime);"></div></div>\n      </div>\n      <div class="xp-card">\n        <div class="xp-label">\n          <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>\n          Defense\n        </div>\n        <div class="xp-val">Level 2</div>\n        <div class="xp-bar-track"><div class="xp-bar-fill" id="xpDefense" style="width:35%;background:var(--purple);"></div></div>\n      </div>\n      <div class="xp-card">\n        <div class="xp-label">\n          <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>\n          Serve\n        </div>\n        <div class="xp-val">Level 3</div>\n        <div class="xp-bar-track"><div class="xp-bar-fill" id="xpServe" style="width:55%;background:var(--amber);"></div></div>\n      </div>\n    </div>\n  </div>\n\n    <div class="screen active" id="screen-home">\n    <div style="padding:18px 18px 0;">\n      <div class="quiz-card" onclick="goToQuiz()">\n        <div class="quiz-badge">\n          <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>\n          Daily quiz\n        </div>\n        <div class="quiz-title" id="quizHomeTitle">Today\'s padel trivia</div>\n        <div class="quiz-sub">Test your knowledge — tactics, pros &amp; rules &middot; +20 XP &middot; 2 min</div>\n        <div class="quiz-btn">\n          <svg class="icon-xs" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21"/></svg>\n          Start\n        </div>\n      </div>\n    </div>\n\n    <div class="section-title">\n      <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>\n      This week\n    </div>\n    <div style="padding:0 18px 22px;">\n      <div class="streak-cal">\n        <div class="day done">M</div>\n        <div class="day done">T</div>\n        <div class="day done">W</div>\n        <div class="day done">T</div>\n        <div class="day today">F</div>\n        <div class="day future">S</div>\n        <div class="day future">S</div>\n      </div>\n    </div>\n\n    <div class="section-title">\n      <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l5.447 2.724A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>\n      Your skill path\n    </div>\n    <div style="padding:0 18px 22px;">\n      <div class="tree">\n        <div class="tree-row">\n          <div class="tree-node done"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>\n          <div class="tree-line done"></div>\n          <div class="tree-node done"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>\n          <div class="tree-line done"></div>\n          <div class="tree-node active"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg></div>\n          <div class="tree-line"></div>\n          <div class="tree-node locked"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg></div>\n        </div>\n        <div class="tree-meta">\n          <span>Serve</span><span>Net rush</span><span>Bandeja</span><span>Vibora</span>\n        </div>\n      </div>\n    </div>\n\n    <div class="section-title">\n      <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>\n      Practice these next\n    </div>\n    <div class="play-list-wrap">\n      <div class="play-row" onclick="watchPlay(\'bandeja-hold\')">\n        <div class="play-icon">\n          <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>\n        </div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Bandeja hold at net</div>\n          <div class="play-meta">\n            <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>\n            Intermediate &middot; 12,400 players learned this\n          </div>\n        </div>\n        <div class="play-check todo"></div>\n      </div>\n      <div class="play-row" onclick="watchPlay(\'cross-lob\')">\n        <div class="play-icon">\n          <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>\n        </div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Cross-court lob</div>\n          <div class="play-meta">\n            <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>\n            Beginner &middot; 28,900 players learned this\n          </div>\n        </div>\n        <div class="play-check done"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>\n      </div>\n    </div>\n  </div>\n\n  <div class="screen" id="screen-plays">\n    <div style="padding:18px 18px 12px;">\n      <div class="search-box">\n        <svg class="search-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>\n        <input type="text" placeholder="Search plays..." id="playsSearch" oninput="filterPlaysList()">\n      </div>\n    </div>\n    <div class="filter-row" style="padding:0 18px 14px;">\n      <div class="filter-chip active" data-lv="all" onclick="selectPlaysFilter(this)">All</div>\n      <div class="filter-chip" data-lv="beginner" onclick="selectPlaysFilter(this)">Beginner</div>\n      <div class="filter-chip" data-lv="intermediate" onclick="selectPlaysFilter(this)">Intermediate</div>\n      <div class="filter-chip" data-lv="advanced" onclick="selectPlaysFilter(this)">Advanced</div>\n    </div>\n\n    <div class="play-list-wrap" id="playsListContainer">\n      <div class="play-row lib-item" data-lv="beginner" data-name="serve net rush" onclick="watchPlay(\'serve-net-rush\')">\n        <div class="play-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Serve + net rush</div>\n          <div class="play-meta"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>Beginner &middot; 31,200 players learned this</div>\n        </div>\n        <div class="play-check done"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>\n      </div>\n      <div class="play-row lib-item" data-lv="beginner" data-name="cross court lob" onclick="watchPlay(\'cross-lob\')">\n        <div class="play-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Cross-court lob</div>\n          <div class="play-meta"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>Beginner &middot; 28,900 players learned this</div>\n        </div>\n        <div class="play-check done"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>\n      </div>\n      <div class="play-row lib-item" data-lv="intermediate" data-name="bandeja hold at net" onclick="watchPlay(\'bandeja-hold\')">\n        <div class="play-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Bandeja hold at net</div>\n          <div class="play-meta"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>Intermediate &middot; 12,400 players learned this</div>\n        </div>\n        <div class="play-check todo"></div>\n      </div>\n      <div class="play-row lib-item" data-lv="intermediate" data-name="chiquita advance" onclick="watchPlay(\'chiquita-advance\')">\n        <div class="play-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Chiquita + advance</div>\n          <div class="play-meta"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>Intermediate &middot; 9,800 players learned this</div>\n        </div>\n        <div class="play-check todo"></div>\n      </div>\n      <div class="play-row lib-item" data-lv="advanced" data-name="vibora side glass" onclick="watchPlay(\'vibora-glass\')">\n        <div class="play-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Vibora to side glass</div>\n          <div class="play-meta"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>Advanced &middot; 4,100 players learned this</div>\n        </div>\n        <div class="play-check todo"></div>\n      </div>\n      <div class="play-row lib-item" data-lv="advanced" data-name="around the post" onclick="watchPlay(\'around-post\')">\n        <div class="play-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Around the post</div>\n          <div class="play-meta"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>Advanced &middot; 2,600 players learned this</div>\n        </div>\n        <div class="play-check todo"></div>\n      </div>\n    </div>\n    <div class="empty-state" id="playsEmpty" style="display:none;">No plays match your search.</div>\n  </div>\n\n  <div class="screen" id="screen-watch">\n    <div class="watch-top">\n      <svg class="icon-sm watch-back" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" onclick="goBack(\'plays\')"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>\n      <div class="watch-title" id="watchTitle">Bandeja hold at net</div>\n      <div style="width:16px;"></div>\n    </div>\n    <div class="watch-court" id="watchCourt">\n      <canvas id="watchCanvas"></canvas>\n      <div class="watch-progress"><div class="watch-progress-fill" id="watchProgressFill"></div></div>\n    </div>\n    <div style="padding:16px 18px;">\n      <div class="step-label">\n        <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>\n        Step 1 of 3\n      </div>\n      <div class="locked-card" id="watchLockedCard">\n        <div class="locked-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg></div>\n        <div class="locked-title">Watch to unlock the quiz</div>\n        <div class="locked-sub">Watch the full play once, then the quiz unlocks below.</div>\n      </div>\n      <div class="locked-card" id="watchUnlockedCard" style="display:none;">\n        <div class="locked-icon" style="background:var(--lime-pale);color:var(--lime-dark);"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>\n        <div class="locked-title">Quiz unlocked</div>\n        <div class="locked-sub">You\'ve watched the full play. Take the quiz to earn XP.</div>\n        <div class="watch-cta-btn" onclick="goToQuizFromWatch()">Take the quiz</div>\n      </div>\n      <div class="zero-note">\n        <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>\n        Watching alone earns 0 XP &mdash; XP comes from the quiz and verified on-court practice.\n      </div>\n    </div>\n  </div>\n\n  <div class="screen" id="screen-quiz-active">\n    <div class="watch-top" style="background:var(--text);">\n      <svg class="icon-sm watch-back" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" onclick="goBack(\'home\')"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>\n      <div class="watch-title">Quick check</div>\n      <div class="xp-pill">\n        <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>\n        +20 XP\n      </div>\n    </div>\n    <div class="quiz-frame">\n      <div class="quiz-pro-tag" id="quizProTag">Inspired by Tapia &amp; Coello\'s net play</div>\n      <div class="quiz-q" id="quizQuestion">Opponent lobs over your head at net. What\'s the correct response?</div>\n      <div id="quizOptsContainer">\n        <div class="quiz-opt" data-correct="false" onclick="selectQuizOpt(this,false)">Smash immediately</div>\n        <div class="quiz-opt" data-correct="true" onclick="selectQuizOpt(this,true)">Bandeja, hold net position</div>\n        <div class="quiz-opt" data-correct="false" onclick="selectQuizOpt(this,false)">Sprint back to baseline</div>\n      </div>\n      <div class="quiz-reward" id="quizReward" style="display:none;"></div>\n    </div>\n  </div>\n\n  <div class="screen" id="screen-checkin">\n    <div class="watch-top" style="background:var(--text);">\n      <svg class="icon-sm watch-back" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" onclick="goBack(\'home\')"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>\n      <div class="watch-title">Confirm practice</div>\n      <div style="width:16px;"></div>\n    </div>\n    <div style="padding:18px;">\n\n      <div class="loc-found" id="locStepA">\n        <div class="loc-pin"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg></div>\n        <div class="loc-title">We detected you\'re at a padel club</div>\n        <div class="loc-club">Padel Lab Madrid</div>\n        <div class="loc-sub">Choose how you\'d like to confirm you drilled this tactic today.</div>\n\n        <div class="tier-list">\n          <div class="tier-card" onclick="confirmByLocation()">\n            <div class="tier-icon loc"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg></div>\n            <div class="tier-text">\n              <div class="tier-name">Confirm by location</div>\n              <div class="tier-desc">Self-reported, verified by GPS</div>\n            </div>\n            <div class="tier-xp">+15 XP</div>\n          </div>\n          <div class="tier-card recommended" onclick="askCoachConfirm()">\n            <div class="tier-badge">More XP</div>\n            <div class="tier-icon coach"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>\n            <div class="tier-text">\n              <div class="tier-name">Ask my coach to confirm</div>\n              <div class="tier-desc">Sent to your coach for a quick yes or no</div>\n            </div>\n            <div class="tier-xp high">+40 XP</div>\n          </div>\n          <div class="tier-card skip" onclick="skipCheckin()">\n            <div class="tier-icon skip-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg></div>\n            <div class="tier-text">\n              <div class="tier-name">Skip for now</div>\n              <div class="tier-desc">Neither option fits right now</div>\n            </div>\n            <div class="tier-xp skip-xp">No XP</div>\n          </div>\n        </div>\n      </div>\n\n      <div class="coach-pending" id="locStepB" style="display:none;">\n        <div class="coach-avatar">T</div>\n        <div class="coach-title">Sent to Toni Alcala</div>\n        <div class="coach-sub">Your coach will get a quick prompt to confirm you drilled this tactic in today\'s session.</div>\n        <div class="coach-status">\n          <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>\n          Awaiting confirmation\n        </div>\n        <div class="fallback-note" onclick="confirmByLocation()">Or confirm now with location for +15 XP instead</div>\n      </div>\n\n    </div>\n  </div>\n\n  <div class="screen" id="screen-saved">\n    <div class="section-title">\n      <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>\n      Your saved plays\n    </div>\n    <div class="play-list-wrap">\n      <div class="play-row" onclick="watchPlay(\'bandeja-hold\')">\n        <div class="play-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>\n        <div style="flex:1;min-width:0;">\n          <div class="play-name">Bandeja hold at net</div>\n          <div class="play-meta"><svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>Intermediate &middot; saved 3 days ago</div>\n        </div>\n        <div class="play-check todo"></div>\n      </div>\n    </div>\n    <div class="empty-hint">Save plays from the library to build your personal practice list.</div>\n  </div>\n\n  <div class="screen" id="screen-profile">\n    <div style="padding:24px 18px;">\n      <div class="profile-card">\n        <div class="profile-avatar">C</div>\n        <div class="profile-name">Carlos Mendez</div>\n        <div class="profile-sub">Member since Jun 2026</div>\n      </div>\n      <div class="profile-stats">\n        <div class="profile-stat">\n          <div class="profile-stat-val">12</div>\n          <div class="profile-stat-label">Day streak</div>\n        </div>\n        <div class="profile-stat">\n          <div class="profile-stat-val">840</div>\n          <div class="profile-stat-label">Total XP</div>\n        </div>\n        <div class="profile-stat">\n          <div class="profile-stat-val">9</div>\n          <div class="profile-stat-label">Plays learned</div>\n        </div>\n      </div>\n      <div class="profile-section-title">Coach</div>\n      <div class="profile-coach-card">\n        <div class="profile-coach-avatar">T</div>\n        <div>\n          <div class="profile-coach-name">Toni Alcala</div>\n          <div class="profile-coach-sub">Padel Lab Madrid</div>\n        </div>\n      </div>\n    </div>\n  </div>\n\n    <div class="bottom-nav">\n    <button class="nav-item active" data-screen="home" onclick="showScreen(\'home\',this)">\n      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>\n      Home\n    </button>\n    <button class="nav-item" data-screen="plays" onclick="showScreen(\'plays\',this)">\n      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>\n      Plays\n    </button>\n    <button class="nav-item" data-screen="quiz-active" onclick="goToQuizFromNav(this)">\n      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>\n      Quiz\n    </button>\n    <button class="nav-item" data-screen="saved" onclick="showScreen(\'saved\',this)">\n      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>\n      Saved\n    </button>\n    <button class="nav-item" data-screen="profile" onclick="showScreen(\'profile\',this)">\n      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>\n      Profile\n    </button>\n  </div>\n\n\n</div>\n\n<script>\n// ── MINI SIMULATOR ENGINE for Watch screen ──────────────────────────────────\nconst WATCH_PLAYS={\n\'bandeja-hold\':{\n  sY:[{x:.32,y:.57},{x:.68,y:.57}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\n  shots:[\n    {l:\'You attack — cross-court volley\',h:\'Y\',f:{x:.32,y:.57},c:{x:.55,y:.35},t:{x:.72,y:.12},ht:.05,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n    {l:\'Opponents LOB over your head\',h:\'O\',f:{x:.72,y:.12},c:{x:.5,y:.4},t:{x:.5,y:.76},ht:.82,d:1500,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n    {l:\'BANDEJA — wide to side glass\',h:\'Y\',f:{x:.68,y:.76},c:{x:.88,y:.45},t:{x:.92,y:.12},ht:.12,d:900,yP:[{x:.32,y:.57},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]}\n  ]\n},\n\'cross-lob\':{\n  sY:[{x:.32,y:.84},{x:.68,y:.84}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\n  shots:[\n    {l:\'Opponents drive to your left\',h:\'O\',f:{x:.72,y:.14},c:{x:.45,y:.5},t:{x:.32,y:.8},ht:.08,d:850,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n    {l:\'Deep cross-court LOB\',h:\'Y\',f:{x:.32,y:.8},c:{x:.72,y:.3},t:{x:.85,y:.07},ht:.85,d:1500,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]}\n  ]\n},\n\'serve-net-rush\':{\n  sY:[{x:.32,y:.88},{x:.68,y:.88}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\n  shots:[\n    {l:\'Serve down the T\',h:\'Y\',f:{x:.68,y:.88},c:{x:.5,y:.65},t:{x:.5,y:.12},ht:.15,d:900,yP:[{x:.32,y:.88},{x:.68,y:.88}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n    {l:\'Both sprint to net\',h:\'M\',f:{x:.5,y:.12},t:{x:.5,y:.12},ht:0,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]}\n  ]\n},\n\'chiquita-advance\':{\n  sY:[{x:.3,y:.74},{x:.7,y:.74}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\n  shots:[\n    {l:\'Opponents attack — fast low ball\',h:\'O\',f:{x:.28,y:.14},c:{x:.35,y:.5},t:{x:.35,y:.7},ht:.04,d:700,yP:[{x:.3,y:.74},{x:.7,y:.74}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n    {l:\'CHIQUITA — low at net feet\',h:\'Y\',f:{x:.35,y:.7},c:{x:.32,y:.52},t:{x:.3,y:.3},ht:.04,d:750,yP:[{x:.3,y:.74},{x:.7,y:.74}],oP:[{x:.28,y:.14},{x:.72,y:.14}]}\n  ]\n},\n\'vibora-glass\':{\n  sY:[{x:.28,y:.62},{x:.7,y:.6}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\n  shots:[\n    {l:\'Opponents LOB — high ball center\',h:\'O\',f:{x:.72,y:.12},c:{x:.58,y:.38},t:{x:.62,y:.56},ht:.82,d:1400,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n    {l:\'VIBORA — to side glass\',h:\'Y\',f:{x:.62,y:.54},c:{x:.97,y:.4},t:{x:.97,y:.1},ht:.07,d:650,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n  ]\n},\n\'around-post\':{\n  sY:[{x:.3,y:.82},{x:.68,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\n  shots:[\n    {l:\'Opponents angle wide left\',h:\'O\',f:{x:.32,y:.14},c:{x:.1,y:.45},t:{x:.06,y:.74},ht:.08,d:850,yP:[{x:.3,y:.82},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n    {l:\'AROUND THE POST!\',h:\'Y\',f:{x:.06,y:.74},c:{x:-.02,y:.52},t:{x:.08,y:.2},ht:.04,d:900,yP:[{x:.06,y:.75},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n  ]\n}\n};\n\nlet wCanvas,wCW,wCH,wShot=0,wShotStart=null,wPlaying=false,wAnimId=null;\n\nfunction wSetup(){\n  wCanvas=document.getElementById(\'watchCanvas\');\n  if(!wCanvas)return;\n  const wrap=document.getElementById(\'watchCourt\');\n  const dpr=window.devicePixelRatio||1;\n  const w=wrap.clientWidth;\n  const h=wrap.clientHeight;\n  wCanvas.width=w*dpr;wCanvas.height=h*dpr;\n  wCanvas.style.width=w+\'px\';wCanvas.style.height=h+\'px\';\n  wCanvas.getContext(\'2d\').setTransform(dpr,0,0,dpr,0,0);\n  wCW=w;wCH=h;\n}\n\nfunction wSc(nx,ny){\n  const tLx=wCW*0.22,tLy=wCH*0.06,tRx=wCW*0.78,tRy=wCH*0.06;\n  const bLx=wCW*0.04,bLy=wCH*0.94,bRx=wCW*0.96,bRy=wCH*0.94;\n  const lx=tLx+(bLx-tLx)*ny,rx=tRx+(bRx-tRx)*ny;\n  const px=lx+(rx-lx)*nx;\n  const py=tLy+(bLy-tLy)*ny;\n  return{x:px,y:py};\n}\n\nfunction wLerp(a,b,t){return a+(b-a)*t;}\nfunction wEase(t){return t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;}\nfunction wBez(p0,p1,p2,t){\n  return{x:(1-t)*(1-t)*p0.x+2*(1-t)*t*p1.x+t*t*p2.x,\n         y:(1-t)*(1-t)*p0.y+2*(1-t)*t*p1.y+t*t*p2.y};\n}\n\nfunction wDrawCourt(ctx){\n  const tLx=wCW*0.22,tRx=wCW*0.78,tY=wCH*0.06;\n  const bLx=wCW*0.04,bRx=wCW*0.96,bY=wCH*0.94;\n  ctx.fillStyle=\'#1a4d7a\';ctx.fillRect(0,0,wCW,wCH);\n  ctx.beginPath();ctx.moveTo(tLx,tY);ctx.lineTo(tRx,tY);ctx.lineTo(bRx,bY);ctx.lineTo(bLx,bY);ctx.closePath();\n  ctx.fillStyle=\'#2e6cb0\';ctx.fill();\n  ctx.strokeStyle=\'rgba(255,255,255,0.9)\';ctx.lineWidth=2.5;ctx.stroke();\n  const nL=wSc(0,0.5),nR=wSc(1,0.5);\n  ctx.beginPath();ctx.moveTo(nL.x,nL.y);ctx.lineTo(nR.x,nR.y);\n  ctx.strokeStyle=\'rgba(255,255,255,0.95)\';ctx.lineWidth=3.5;ctx.stroke();\n  const sL1=wSc(0,0.15),sR1=wSc(1,0.15),sL2=wSc(0,0.85),sR2=wSc(1,0.85);\n  ctx.strokeStyle=\'rgba(255,255,255,0.4)\';ctx.lineWidth=1.5;\n  ctx.beginPath();ctx.moveTo(sL1.x,sL1.y);ctx.lineTo(sR1.x,sR1.y);ctx.stroke();\n  ctx.beginPath();ctx.moveTo(sL2.x,sL2.y);ctx.lineTo(sR2.x,sR2.y);ctx.stroke();\n  const cN=wSc(.5,.5),cS1=wSc(.5,.15),cS2=wSc(.5,.85);\n  ctx.strokeStyle=\'rgba(255,255,255,0.3)\';ctx.lineWidth=1.2;\n  ctx.beginPath();ctx.moveTo(cS1.x,cS1.y);ctx.lineTo(cN.x,cN.y);ctx.stroke();\n  ctx.beginPath();ctx.moveTo(cN.x,cN.y);ctx.lineTo(cS2.x,cS2.y);ctx.stroke();\n}\n\nfunction wPlayerSize(ny){return Math.round(wCW*(0.03+ny*0.024));}\n\nfunction wDrawPlayer(ctx,nx,ny,fill,ring,label){\n  const p=wSc(nx,ny);\n  const r=wPlayerSize(ny);\n  const bodyH=r*1.6;\n  ctx.beginPath();ctx.ellipse(p.x,p.y+r*0.25,r*0.9,r*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=\'rgba(0,0,0,0.45)\';ctx.fill();\n  ctx.beginPath();\n  ctx.moveTo(p.x-r,p.y);ctx.lineTo(p.x+r,p.y);\n  ctx.lineTo(p.x+r*0.9,p.y-bodyH);ctx.lineTo(p.x-r*0.9,p.y-bodyH);\n  ctx.closePath();ctx.fillStyle=fill;ctx.fill();\n  ctx.beginPath();ctx.ellipse(p.x,p.y-bodyH,r*0.9,r*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=ring;ctx.fill();\n  ctx.fillStyle=\'rgba(255,255,255,0.95)\';\n  ctx.font=\'bold \'+Math.round(r*0.75)+\'px Inter,sans-serif\';\n  ctx.textAlign=\'center\';ctx.textBaseline=\'middle\';\n  ctx.fillText(label,p.x,p.y-bodyH+r*0.08);\n}\n\nfunction wDrawBall(ctx,nx,ny,h){\n  const p=wSc(nx,ny);\n  const pr=wPlayerSize(ny);\n  const lift=h*wCH*0.14;\n  const r=pr*0.42+h*pr*0.3;\n  ctx.beginPath();ctx.ellipse(p.x,p.y,r*0.9,r*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=\'rgba(0,0,0,\'+(0.38-h*0.18)+\')\';ctx.fill();\n  ctx.beginPath();ctx.arc(p.x,p.y-lift,r,0,Math.PI*2);\n  ctx.fillStyle=\'#d4e820\';ctx.fill();\n  ctx.strokeStyle=\'#9aac00\';ctx.lineWidth=1.2;ctx.stroke();\n}\n\nfunction wRender(t){\n  const ctx=wCanvas.getContext(\'2d\');\n  ctx.clearRect(0,0,wCW,wCH);\n  wDrawCourt(ctx);\n  const play=WATCH_PLAYS[currentPlayId]||WATCH_PLAYS[\'bandeja-hold\'];\n  const shots=play.shots;\n  const et=wEase(Math.min(t,1));\n  const s=shots[Math.min(wShot,shots.length-1)];\n  const prevY=wShot===0?play.sY:(shots[wShot-1].yP||play.sY);\n  const prevO=wShot===0?play.sO:(shots[wShot-1].oP||play.sO);\n  const curY=s.yP||prevY;const curO=s.oP||prevO;\n  const py=curY.map((p,i)=>({x:wLerp(prevY[i].x,p.x,et),y:wLerp(prevY[i].y,p.y,et)}));\n  const po=curO.map((p,i)=>({x:wLerp(prevO[i].x,p.x,et),y:wLerp(prevO[i].y,p.y,et)}));\n  po.forEach((p,i)=>wDrawPlayer(ctx,p.x,p.y,\'#50000e\',\'#dc2626\',[\'O1\',\'O2\'][i]));\n  py.forEach((p,i)=>wDrawPlayer(ctx,p.x,p.y,\'#1a0a2e\',i===1?\'#3ecf7e\':\'#7c4de0\',[\'Y1\',\'Y2\'][i]));\n  if(wShot<shots.length&&s.h!==\'M\'){\n    const bp=wBez(s.f,s.c,s.t,et);\n    const h=(s.ht||0)*Math.sin(et*Math.PI);\n    wDrawBall(ctx,bp.x,bp.y,h);\n  } else if(wShot>0){\n    const last=shots[Math.min(wShot-1,shots.length-1)];\n    wDrawBall(ctx,last.t.x,last.t.y,0);\n  }\n}\n\nfunction wAnimFrame(ts){\n  const play=WATCH_PLAYS[currentPlayId]||WATCH_PLAYS[\'bandeja-hold\'];\n  const shots=play.shots;\n  if(!wShotStart)wShotStart=ts;\n  const s=shots[wShot];\n  const t=Math.min((ts-wShotStart)/s.d,1);\n  wRender(t);\n  const total=shots.reduce((a,x)=>a+x.d,0);\n  const done=shots.slice(0,wShot).reduce((a,x)=>a+x.d,0)+(ts-wShotStart);\n  document.getElementById(\'watchProgressFill\').style.width=Math.min(done/total*100,100)+\'%\';\n  if(t>=1){\n    wShot++;\n    if(wShot>=shots.length){\n      wPlaying=false;\n      document.getElementById(\'watchLockedCard\').style.display=\'none\';\n      document.getElementById(\'watchUnlockedCard\').style.display=\'block\';\n      showToast(\'Play watched — quiz unlocked\');\n      return;\n    }\n    wShotStart=null;\n  }\n  if(wPlaying)wAnimId=requestAnimationFrame(wAnimFrame);\n}\n\nfunction wStartAnim(){\n  wShot=0;wShotStart=null;wPlaying=true;\n  document.getElementById(\'watchProgressFill\').style.width=\'0%\';\n  document.getElementById(\'watchLockedCard\').style.display=\'block\';\n  document.getElementById(\'watchUnlockedCard\').style.display=\'none\';\n  if(wAnimId)cancelAnimationFrame(wAnimId);\n  wAnimId=requestAnimationFrame(wAnimFrame);\n}\n\nwindow.addEventListener(\'resize\',()=>{\n  if(document.getElementById(\'screen-watch\').classList.contains(\'active\')){\n    wSetup();\n  }\n});\n\n\nfunction showToast(msg){\n  const t=document.getElementById(\'toast\');\n  t.textContent=msg;\n  t.style.display=\'block\';\n  setTimeout(()=>t.style.display=\'none\',2800);\n}\n\nfunction showScreen(name,navEl){\n  document.querySelectorAll(\'.screen\').forEach(s=>s.classList.remove(\'active\'));\n  document.getElementById(\'screen-\'+name).classList.add(\'active\');\n  if(navEl){\n    document.querySelectorAll(\'.nav-item\').forEach(n=>n.classList.remove(\'active\'));\n    navEl.classList.add(\'active\');\n  }\n  document.getElementById(\'appShell\').scrollTop=0;\n  const scr=document.getElementById(\'screen-\'+name);\n  if(scr)scr.scrollTop=0;\n}\n\nfunction goBack(name){\n  const navBtn=document.querySelector(\'.nav-item[data-screen="\'+name+\'"]\');\n  showScreen(name,navBtn);\n}\n\nlet currentPlayId=null;\nconst playNames={\n  \'bandeja-hold\':\'Bandeja hold at net\',\n  \'cross-lob\':\'Cross-court lob\',\n  \'serve-net-rush\':\'Serve + net rush\',\n  \'chiquita-advance\':\'Chiquita + advance\',\n  \'vibora-glass\':\'Vibora to side glass\',\n  \'around-post\':\'Around the post\'\n};\n\nfunction watchPlay(playId){\n  currentPlayId=playId;\n  document.getElementById(\'watchTitle\').textContent=playNames[playId]||\'Padel play\';\n  document.getElementById(\'watchLockedCard\').style.display=\'block\';\n  document.getElementById(\'watchUnlockedCard\').style.display=\'none\';\n  showScreen(\'watch\',null);\n  setTimeout(()=>{\n    wSetup();\n    wStartAnim();\n  },50);\n}\n\nfunction goToQuizFromWatch(){\n  quizContext=\'play\';\n  enterQuizScreen();\n}\n\nfunction goToQuiz(){\n  quizContext=\'daily\';\n  enterQuizScreen();\n}\n\nfunction goToQuizFromNav(navEl){\n  quizContext=\'daily\';\n  enterQuizScreen(navEl);\n}\n\nfunction enterQuizScreen(navEl){\n  resetQuizScreen();\n  if(isQuizLocked()){\n    showScreen(\'quiz-active\',navEl||document.querySelector(\'.nav-item[data-screen="quiz-active"]\'));\n    showQuizLockedState();\n  } else {\n    pickRandomQuiz();\n    showScreen(\'quiz-active\',navEl||document.querySelector(\'.nav-item[data-screen="quiz-active"]\'));\n  }\n}\n\nfunction resetQuizScreen(){\n  document.querySelectorAll(\'.quiz-opt\').forEach(o=>{\n    o.classList.remove(\'correct-sel\');\n    o.classList.remove(\'wrong-sel\');\n    o.style.pointerEvents=\'\';\n    o.style.cursor=\'\';\n  });\n  const reward=document.getElementById(\'quizReward\');\n  reward.style.display=\'none\';\n  reward.style.flexDirection=\'\';\n  reward.style.alignItems=\'\';\n  reward.style.gap=\'\';\n  reward.style.background=\'\';\n  reward.style.borderColor=\'\';\n  document.getElementById(\'quizProTag\').style.display=\'inline-flex\';\n  if(quizCountdownInterval){clearInterval(quizCountdownInterval);quizCountdownInterval=null;}\n}\n\nconst QUIZ_BANK_TACTICAL=[\n  {\n    type:"tactical",\n    pro:"Tactical scenario",\n    q:"Opponent lobs over your head at net. What\'s the correct response?",\n    opts:["Smash immediately","Bandeja, hold net position","Sprint back to baseline"],\n    correct:1,\n    explanation:"The bandeja is the right call — it gives you a controlled overhead that keeps you at the net. Smashing risks losing position; sprinting back gives your opponents the net for free."\n  },\n  {\n    type:"tactical",\n    pro:"Tactical scenario",\n    q:"You\'re pinned at the baseline under pressure. What\'s the highest-percentage shot?",\n    opts:["A flat drive down the middle","A deep lob to reset the point","Run around for a forehand smash"],\n    correct:1,\n    explanation:"A deep lob is the classic defensive reset in padel — it buys time, forces opponents off the net, and lets you recover position. A flat drive under pressure is low-percentage."\n  },\n  {\n    type:"tactical",\n    pro:"Tactical scenario",\n    q:"Your partner is pulled wide to the side glass. What should you do at net?",\n    opts:["Stay in your original position","Shift toward the middle to cover the open court","Move to the same side as your partner"],\n    correct:1,\n    explanation:"When your partner is dragged wide, you must shift centrally to cover the diagonal. Staying put leaves the middle open; moving the same way as your partner leaves the other side completely exposed."\n  },\n  {\n    type:"tactical",\n    pro:"Tactical scenario",\n    q:"You\'ve just hit a strong lob and your opponents are scrambling. What\'s next?",\n    opts:["Relax and wait for their return","Advance to net immediately behind the lob","Stay back in case they counter-lob"],\n    correct:1,\n    explanation:"A good lob is your chance to take the net. Advance behind it immediately — if you stay back you hand the initiative back to your opponents even after winning the exchange."\n  }\n];\n\nconst QUIZ_BANK_NEWS=[\n  {\n    type:"news",\n    pro:"Padel world ranking",\n    q:"As of mid-2026, who holds the world No.1 men\'s padel ranking?",\n    opts:["Galán & Chingotto","Tapia & Coello","Lebrón & Augsburger"],\n    correct:1,\n    explanation:"Tapia & Coello have dominated the ATP/Premier Padel circuit since 2024, consistently ranked No.1. Galán & Lebrón split as a pair, reforming with new partners."\n  },\n  {\n    type:"news",\n    pro:"Padel records",\n    q:"What is the longest winning streak in professional padel history?",\n    opts:["47 consecutive match wins","30 consecutive match wins","60 consecutive match wins"],\n    correct:0,\n    explanation:"Belasteguín & Díaz held a 47-match winning streak — one of the most dominant runs in the history of any racket sport, spanning multiple consecutive tournaments."\n  },\n  {\n    type:"news",\n    pro:"Padel history",\n    q:"Which player held the world No.1 ranking for a record 16 consecutive seasons?",\n    opts:["Fernando Belasteguín","Juan Lebrón","Alejandro Galán"],\n    correct:0,\n    explanation:"Fernando Belasteguín held No.1 from 2002 to 2018 — 16 consecutive seasons. It remains the longest dominance in padel history and rivals any achievement in racket sports."\n  },\n  {\n    type:"news",\n    pro:"Padel world ranking",\n    q:"Which country has the most players in the men\'s world top 100 as of 2026?",\n    opts:["Argentina","Spain","Italy"],\n    correct:1,\n    explanation:"Spain leads the men\'s top 100 with the most represented players, driven by a massive club infrastructure and professional circuit. Argentina is a close second with a strong tradition of padel."\n  },\n  {\n    type:"news",\n    pro:"Padel women\'s ranking",\n    q:"Which pair leads the women\'s world ranking in 2026?",\n    opts:["Sánchez & Josemaría","Triay & Brea","Mapi & Majo Sánchez Alayeto"],\n    correct:1,\n    explanation:"Triay & Brea have been the dominant women\'s pair since 2022, winning multiple Premier Padel titles. Gemma Triay is widely regarded as the best women\'s player in the world."\n  }\n];\n\nconst QUIZ_BANK=[...QUIZ_BANK_TACTICAL,...QUIZ_BANK_NEWS];\n\nlet currentQuizIdx=0;\n\nfunction pickRandomQuiz(){\n  currentQuizIdx=Math.floor(Math.random()*QUIZ_BANK.length);\n  const quiz=QUIZ_BANK[currentQuizIdx];\n  const tag=document.getElementById(\'quizProTag\');\n  tag.textContent=quiz.pro;\n  tag.className=quiz.type===\'news\'?\'quiz-pro-tag news-tag\':\'quiz-pro-tag\';\n  const qEl=document.getElementById(\'quizQuestion\');\n  qEl.textContent=quiz.q;\n  qEl.dataset.explanation=quiz.explanation||\'\';\n  const container=document.getElementById(\'quizOptsContainer\');\n  container.innerHTML=\'\';\n  quiz.opts.forEach((opt,i)=>{\n    const div=document.createElement(\'div\');\n    div.className=\'quiz-opt\';\n    div.dataset.correct=(i===quiz.correct)?\'true\':\'false\';\n    div.textContent=opt;\n    div.onclick=()=>selectQuizOpt(div,i===quiz.correct);\n    container.appendChild(div);\n  });\n}\n\nfunction skipCheckin(){\n  showToast(\'No problem — come back anytime to confirm practice\');\n  setTimeout(()=>showScreen(\'home\',document.querySelector(\'.nav-item[data-screen="home"]\')),700);\n}\n\nlet quizAnswered=false;\nlet quizContext=\'daily\';\nlet quizWrongCount=0;\nlet quizCountdownInterval=null;\nconst QUIZ_LOCKOUT_MS=60*60*1000;\nconst QUIZ_LOCKOUT_KEY=\'orbis_quiz_lockout_until\';\nconst QUIZ_WRONG_KEY=\'orbis_quiz_wrong_count\';\n\nfunction getQuizLockoutUntil(){\n  const v=localStorage.getItem(QUIZ_LOCKOUT_KEY);\n  return v?parseInt(v,10):0;\n}\n\nfunction isQuizLocked(){\n  return getQuizLockoutUntil()>Date.now();\n}\n\nfunction getQuizWrongCount(){\n  const v=localStorage.getItem(QUIZ_WRONG_KEY);\n  return v?parseInt(v,10):0;\n}\n\nfunction setQuizWrongCount(n){\n  localStorage.setItem(QUIZ_WRONG_KEY,String(n));\n}\n\nfunction lockQuizForOneHour(){\n  const until=Date.now()+QUIZ_LOCKOUT_MS;\n  localStorage.setItem(QUIZ_LOCKOUT_KEY,String(until));\n  setQuizWrongCount(0);\n}\n\nfunction clearQuizLockout(){\n  localStorage.removeItem(QUIZ_LOCKOUT_KEY);\n  setQuizWrongCount(0);\n}\n\nfunction formatCountdown(ms){\n  const totalSec=Math.max(0,Math.ceil(ms/1000));\n  const m=Math.floor(totalSec/60);\n  const s=totalSec%60;\n  return (m<10?\'0\':\'\')+m+\':\'+(s<10?\'0\':\'\')+s;\n}\n\nfunction showQuizLockedState(){\n  document.getElementById(\'quizProTag\').style.display=\'none\';\n  document.getElementById(\'quizQuestion\').textContent=\'Quiz locked after 2 missed answers\';\n  const container=document.getElementById(\'quizOptsContainer\');\n  container.innerHTML=\'\';\n  document.getElementById(\'quizReward\').style.display=\'none\';\n  const lockCard=document.createElement(\'div\');\n  lockCard.className=\'quiz-lock-card\';\n  lockCard.innerHTML=\'<div class="quiz-lock-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div><div class="quiz-lock-text">Try again in</div><div class="quiz-lock-timer" id="quizLockTimer">60:00</div>\';\n  container.appendChild(lockCard);\n  if(quizCountdownInterval)clearInterval(quizCountdownInterval);\n  quizCountdownInterval=setInterval(()=>{\n    const remaining=getQuizLockoutUntil()-Date.now();\n    if(remaining<=0){\n      clearInterval(quizCountdownInterval);\n      clearQuizLockout();\n      pickRandomQuiz();\n      return;\n    }\n    const timerEl=document.getElementById(\'quizLockTimer\');\n    if(timerEl)timerEl.textContent=formatCountdown(remaining);\n  },1000);\n}\n\nfunction selectQuizOpt(el,isCorrect){\n  if(quizAnswered)return;\n  quizAnswered=true;\n\n  // Disable all options immediately\n  document.querySelectorAll(\'.quiz-opt\').forEach(o=>{\n    o.style.pointerEvents=\'none\';\n    o.style.cursor=\'default\';\n  });\n\n  if(isCorrect){\n    el.classList.add(\'correct-sel\');\n    setQuizWrongCount(0);\n    const reward=document.getElementById(\'quizReward\');\n    reward.innerHTML=\'<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>Correct — +20 XP earned\';\n    reward.style.display=\'flex\';\n    setTimeout(()=>{\n      quizAnswered=false;\n      if(quizContext===\'play\'){\n        showScreen(\'checkin\',null);\n        document.getElementById(\'locStepA\').style.display=\'block\';\n        document.getElementById(\'locStepB\').style.display=\'none\';\n      } else {\n        showQuizResultCard();\n      }\n    },1400);\n  } else {\n    el.classList.add(\'wrong-sel\');\n    const wrongCount=getQuizWrongCount()+1;\n    setQuizWrongCount(wrongCount);\n\n    // Reveal the correct answer immediately\n    document.querySelectorAll(\'.quiz-opt\').forEach(o=>{\n      if(o.dataset.correct===\'true\') o.classList.add(\'correct-sel\');\n    });\n\n    // Show explanation and a Continue button\n    const reward=document.getElementById(\'quizReward\');\n    const explanation=document.getElementById(\'quizQuestion\').dataset.explanation||\'\';\n    reward.style.display=\'flex\';\n    reward.style.flexDirection=\'column\';\n    reward.style.alignItems=\'flex-start\';\n    reward.style.gap=\'10px\';\n    reward.style.background=\'rgba(248,113,113,.08)\';\n    reward.style.borderColor=\'rgba(248,113,113,.25)\';\n    reward.innerHTML=`\n      <div style="display:flex;align-items:center;gap:7px;font-size:12.5px;font-weight:700;color:#f87171;">\n        <svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>\n        Not quite\n      </div>\n      ${explanation?`<div style="font-size:11px;color:rgba(255,255,255,.55);line-height:1.5;">${explanation}</div>`:\'\'}\n      <div style="width:100%;background:var(--lime);color:#0a2a16;font-size:12.5px;font-weight:700;padding:10px;border-radius:9px;text-align:center;cursor:pointer;"\n           onclick="afterWrongAnswer()">Got it — continue</div>\n    `;\n\n    if(wrongCount>=2){\n      lockQuizForOneHour();\n    }\n  }\n}\n\nfunction afterWrongAnswer(){\n  quizAnswered=false;\n  const isLocked=getQuizLockoutUntil()>Date.now();\n  if(isLocked){\n    showQuizLockedState();\n  } else {\n    showScreen(\'home\',document.querySelector(\'.nav-item[data-screen="home"]\'));\n  }\n}\n\nfunction showQuizResultCard(){\n  document.getElementById(\'quizProTag\').style.display=\'none\';\n  document.getElementById(\'quizQuestion\').textContent=\'\';\n  const container=document.getElementById(\'quizOptsContainer\');\n  container.innerHTML=\'\';\n  document.getElementById(\'quizReward\').style.display=\'none\';\n  const resultCard=document.createElement(\'div\');\n  resultCard.className=\'quiz-result-card\';\n  resultCard.innerHTML=\'<div class="quiz-result-icon"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div><div class="quiz-result-title">Daily quiz complete</div><div class="quiz-result-xp">+20 XP earned</div><div class="quiz-result-btn" id="quizResultHomeBtn">Back to home</div>\';\n  container.appendChild(resultCard);\n  document.getElementById(\'quizResultHomeBtn\').onclick=()=>{\n    showScreen(\'home\',document.querySelector(\'.nav-item[data-screen="home"]\'));\n  };\n}\n\nfunction confirmByLocation(){\n  showToast(\'Practice confirmed by location — +15 XP, streak extended\');\n  setTimeout(()=>showScreen(\'home\',document.querySelector(\'.nav-item[data-screen="home"]\')),900);\n}\n\nfunction askCoachConfirm(){\n  document.getElementById(\'locStepA\').style.display=\'none\';\n  document.getElementById(\'locStepB\').style.display=\'block\';\n}\n\nfunction selectPlaysFilter(el){\n  document.querySelectorAll(\'.filter-chip\').forEach(c=>c.classList.remove(\'active\'));\n  el.classList.add(\'active\');\n  filterPlaysList();\n}\n\nfunction filterPlaysList(){\n  const query=document.getElementById(\'playsSearch\').value.trim().toLowerCase();\n  const activeFilter=document.querySelector(\'.filter-chip.active\').dataset.lv;\n  const items=document.querySelectorAll(\'.lib-item\');\n  let visibleCount=0;\n  items.forEach(item=>{\n    const matchesQuery=!query||item.dataset.name.includes(query);\n    const matchesLevel=activeFilter===\'all\'||item.dataset.lv===activeFilter;\n    const show=matchesQuery&&matchesLevel;\n    item.style.display=show?\'flex\':\'none\';\n    if(show)visibleCount++;\n  });\n  document.getElementById(\'playsEmpty\').style.display=visibleCount===0?\'block\':\'none\';\n}\n\n</script>\n</body>\n</html>\n')

from mangum import Mangum
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
