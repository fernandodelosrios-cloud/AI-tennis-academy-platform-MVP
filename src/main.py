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
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbis AI — Tennis & Padel Coaching Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700;9..40,800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
:root{--navy:#3d1a6e;--navy2:#4a2080;--lime:#3ecf7e;--lime-dark:#2aad62;--lime-pale:#d4f5e5;--bg:#f2f0f7;--text:#1a0a2e;--text2:#5a4a7a;--text3:#9a8aaa;--border:#e2e6ef;--surface:#fff;}
html{scroll-behavior:smooth;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;}

/* Nav */
.nav{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(61,26,110,.97);backdrop-filter:blur(12px);box-shadow:0 2px 20px rgba(61,26,110,.3);}
.nav-inner{max-width:1200px;margin:0 auto;padding:0 24px;height:64px;display:flex;align-items:center;justify-content:space-between;}
.logo{display:flex;align-items:center;gap:10px;text-decoration:none;}
.logo-text{font-size:18px;font-weight:800;color:#fff;letter-spacing:-.02em;}
.logo-text span{color:var(--lime);}
.logo-sub{font-size:8px;color:rgba(255,255,255,.4);letter-spacing:.16em;text-transform:uppercase;margin-top:1px;}
.nav-links{display:flex;align-items:center;gap:8px;}
.nav-link{color:rgba(255,255,255,.7);text-decoration:none;font-size:14px;font-weight:500;padding:6px 12px;border-radius:6px;transition:color .2s;}
.nav-link:hover{color:#fff;}
.btn-waitlist{background:var(--lime);color:var(--navy);border-radius:7px;padding:8px 18px;font-size:13px;font-weight:700;cursor:pointer;text-decoration:none;transition:all .2s;}
.btn-waitlist:hover{background:#4de08e;transform:translateY(-1px);}

/* Hero */
.hero{min-height:100vh;background:linear-gradient(160deg,#2a0f52 0%,#3d1a6e 40%,#1a0a2e 100%);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:100px 24px 80px;text-align:center;position:relative;overflow:hidden;}
.hero::before{content:'';position:absolute;inset:0;background-image:radial-gradient(circle at 20% 50%,rgba(62,207,126,.06) 0%,transparent 50%),radial-gradient(circle at 80% 20%,rgba(62,207,126,.04) 0%,transparent 40%);}
.hero-badge{background:rgba(62,207,126,.12);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:6px 18px;font-size:12px;color:var(--lime);font-weight:700;margin-bottom:28px;display:inline-block;letter-spacing:.06em;text-transform:uppercase;}
.hero-title{font-size:clamp(38px,6vw,76px);font-weight:800;color:#fff;letter-spacing:-.04em;line-height:1.02;margin-bottom:22px;max-width:820px;}
.hero-title .accent{color:var(--lime);}
.hero-sub{font-size:clamp(16px,2vw,20px);color:rgba(255,255,255,.55);line-height:1.7;max-width:540px;margin-bottom:44px;}
.btn-hero{background:var(--lime);color:var(--navy);border:none;border-radius:10px;padding:16px 36px;font-size:16px;font-weight:700;cursor:pointer;text-decoration:none;transition:all .2s;display:inline-flex;align-items:center;gap:8px;box-shadow:0 4px 20px rgba(62,207,126,.25);}
.btn-hero:hover{background:#4de08e;transform:translateY(-2px);box-shadow:0 8px 32px rgba(62,207,126,.35);}
.hero-note{font-size:13px;color:rgba(255,255,255,.3);margin-top:14px;}
.hero-pain{display:flex;gap:32px;justify-content:center;flex-wrap:wrap;margin-top:60px;}
.pain-item{display:flex;align-items:center;gap:8px;font-size:13px;color:rgba(255,255,255,.45);}
.pain-dot{width:6px;height:6px;border-radius:50%;background:var(--lime);flex-shrink:0;}

/* Pain section */
.pain-section{background:#fff;padding:80px 24px;}
.container{max-width:1140px;margin:0 auto;}
.section-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--lime-dark);margin-bottom:10px;}
.section-title{font-size:clamp(28px,4vw,46px);font-weight:800;color:var(--text);letter-spacing:-.03em;line-height:1.08;margin-bottom:14px;}
.section-sub{font-size:17px;color:var(--text2);line-height:1.65;max-width:520px;}
.pain-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px;margin-top:48px;}
.pain-card{border-radius:14px;padding:28px;border:1px solid var(--border);background:var(--bg);transition:all .25s;}
.pain-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(61,26,110,.09);border-color:rgba(61,26,110,.15);}
.pain-icon{width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;margin-bottom:18px;}
.pain-icon svg{width:24px;height:24px;}
.pain-icon.purple{background:rgba(61,26,110,.08);}
.pain-icon.lime{background:var(--lime-pale);}
.pain-icon.amber{background:#fef3c7;}
.pain-icon.red{background:#fee2e2;}
.pain-title{font-size:16px;font-weight:700;color:var(--text);margin-bottom:8px;}
.pain-desc{font-size:14px;color:var(--text2);line-height:1.65;}
.pain-arrow{display:flex;align-items:center;gap:6px;margin-top:14px;font-size:12px;font-weight:600;color:var(--lime-dark);}

/* Features tabs */
.tabs-section{background:var(--bg);padding:80px 24px;}
.tabs{display:flex;gap:0;border-bottom:2px solid var(--border);margin-bottom:48px;overflow-x:auto;}
.tab{padding:14px 22px;font-size:14px;font-weight:600;color:var(--text3);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;white-space:nowrap;transition:all .2s;display:flex;align-items:center;gap:8px;}
.tab svg{width:16px;height:16px;opacity:.5;}
.tab.active{color:var(--navy);border-bottom-color:var(--navy);}
.tab.active svg{opacity:1;}
.tab-content{display:none;animation:fadeIn .3s ease;}
.tab-content.active{display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:center;}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.tab-text h3{font-size:30px;font-weight:800;color:var(--text);letter-spacing:-.025em;margin-bottom:14px;line-height:1.15;}
.tab-text p{font-size:16px;color:var(--text2);line-height:1.7;margin-bottom:24px;}
.tab-feats{display:flex;flex-direction:column;gap:10px;}
.tab-feat{display:flex;align-items:center;gap:10px;font-size:14px;color:var(--text2);}
.tab-feat-check{width:20px;height:20px;border-radius:50%;background:var(--lime-pale);display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.tab-feat-check svg{width:10px;height:10px;color:var(--lime-dark);}
.tab-visual{background:linear-gradient(135deg,#ece9f4,#ddd8ec);border-radius:18px;padding:28px;min-height:340px;display:flex;align-items:center;justify-content:center;}
.mock{background:#fff;border-radius:14px;box-shadow:0 6px 32px rgba(61,26,110,.12);padding:20px;width:100%;max-width:340px;}
.mock-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border);}
.mock-hdr-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--text3);}
.mock-badge{border-radius:20px;padding:3px 9px;font-size:10px;font-weight:700;}
.mock-badge.green{background:var(--lime-pale);color:var(--lime-dark);}
.mock-badge.purple{background:rgba(61,26,110,.08);color:var(--navy);}
.mock-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:.5px solid var(--border);font-size:13px;color:var(--text2);}
.mock-row:last-of-type{border:none;}
.mock-val{font-weight:700;color:var(--navy);}
.mock-val.green{color:#16a34a;}
.mock-bar-row{margin-top:14px;}
.mock-bar-label{display:flex;justify-content:space-between;font-size:11px;color:var(--text3);margin-bottom:4px;}
.mock-bar{height:6px;background:var(--border);border-radius:3px;overflow:hidden;margin-bottom:8px;}
.mock-fill{height:100%;border-radius:3px;}
.mock-fill.navy{background:var(--navy);}
.mock-fill.lime{background:var(--lime);}
.mock-fill.amber{background:#f59e0b;}
.chat-bubble{border-radius:10px;padding:10px 13px;font-size:12px;line-height:1.5;margin-bottom:8px;max-width:92%;}
.chat-bubble.user{background:var(--bg);color:var(--text2);border-radius:10px 10px 10px 2px;}
.chat-bubble.ai{background:var(--navy);color:rgba(255,255,255,.88);border-radius:10px 10px 2px 10px;margin-left:auto;}

/* Why section */
.why-section{background:#fff;padding:80px 24px;}
.why-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin-top:48px;}
.why-card{border-radius:14px;padding:26px;border:1px solid var(--border);transition:all .25s;cursor:default;}
.why-card:hover{transform:translateY(-4px);box-shadow:0 10px 32px rgba(61,26,110,.09);border-color:rgba(61,26,110,.15);}
.why-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;margin-bottom:16px;}
.why-icon svg{width:22px;height:22px;}
.why-title{font-size:15px;font-weight:700;color:var(--text);margin-bottom:8px;}
.why-desc{font-size:13px;color:var(--text2);line-height:1.65;}

/* Comparison */
.comp-section{background:var(--navy);padding:80px 24px;}
.comp-title{font-size:clamp(28px,4vw,44px);font-weight:800;color:#fff;letter-spacing:-.03em;margin-bottom:12px;}
.comp-sub{font-size:16px;color:rgba(255,255,255,.45);margin-bottom:48px;}
.comp-table{background:rgba(255,255,255,.04);border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,.08);}
.comp-row{display:grid;grid-template-columns:2fr 1fr 1fr;border-bottom:1px solid rgba(255,255,255,.05);}
.comp-row:last-child{border:none;}
.comp-row.hdr{background:rgba(255,255,255,.06);}
.comp-cell{padding:14px 20px;font-size:13px;color:rgba(255,255,255,.6);display:flex;align-items:center;}
.comp-cell.feat{color:rgba(255,255,255,.4);font-size:12px;}
.comp-hdr{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:rgba(255,255,255,.35);}
.comp-hdr.orbis{color:var(--lime);}
.check-yes{color:var(--lime);font-size:17px;font-weight:700;}
.check-no{color:rgba(255,255,255,.15);font-size:17px;}

/* Waitlist modal */
.modal-overlay{position:fixed;inset:0;background:rgba(10,0,30,.6);backdrop-filter:blur(4px);z-index:999;display:flex;align-items:center;justify-content:center;padding:24px;opacity:0;pointer-events:none;transition:opacity .25s;}
.modal-overlay.open{opacity:1;pointer-events:all;}
.modal{background:#fff;border-radius:20px;padding:40px;max-width:440px;width:100%;box-shadow:0 24px 64px rgba(61,26,110,.2);transform:translateY(16px);transition:transform .25s;}
.modal-overlay.open .modal{transform:translateY(0);}
.modal-logo{display:flex;align-items:center;gap:8px;margin-bottom:24px;}
.modal-title{font-size:22px;font-weight:800;color:var(--text);letter-spacing:-.02em;margin-bottom:6px;}
.modal-sub{font-size:14px;color:var(--text2);margin-bottom:28px;line-height:1.6;}
.field{margin-bottom:16px;}
.field label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text3);margin-bottom:6px;}
.field input,.field select{width:100%;border:1.5px solid var(--border);border-radius:8px;padding:11px 14px;font-size:14px;font-family:inherit;color:var(--text);outline:none;transition:border .15s;background:#fff;}
.field input:focus,.field select:focus{border-color:var(--navy);}
.field-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.btn-submit{width:100%;background:var(--navy);color:#fff;border:none;border-radius:8px;padding:13px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:4px;transition:all .2s;}
.btn-submit:hover{background:var(--navy2);}
.btn-submit:disabled{opacity:.5;cursor:not-allowed;}
.modal-close{position:absolute;top:16px;right:16px;background:none;border:none;font-size:20px;cursor:pointer;color:var(--text3);line-height:1;}
.modal-success{text-align:center;padding:20px 0;}
.modal-success .check-big{width:56px;height:56px;background:var(--lime-pale);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:24px;}

/* Footer */
.footer{background:#1a0a2e;padding:48px 24px 24px;}
.footer-inner{max-width:1140px;margin:0 auto;}
.footer-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px;flex-wrap:wrap;gap:28px;}
.footer-brand p{font-size:13px;color:rgba(255,255,255,.35);margin-top:10px;max-width:200px;line-height:1.6;}
.footer-links{display:flex;gap:48px;flex-wrap:wrap;}
.footer-col h4{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:rgba(255,255,255,.25);margin-bottom:14px;}
.footer-col a{display:block;font-size:13px;color:rgba(255,255,255,.45);text-decoration:none;margin-bottom:10px;transition:color .2s;}
.footer-col a:hover{color:#fff;}
.footer-bottom{border-top:1px solid rgba(255,255,255,.05);padding-top:20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;}
.footer-bottom p{font-size:12px;color:rgba(255,255,255,.2);}

@media(max-width:768px){
  .tab-content.active{grid-template-columns:1fr;}
  .comp-row{grid-template-columns:1.8fr 1fr 1fr;}
  .nav-links .nav-link{display:none;}
  .field-row{grid-template-columns:1fr;}
  .footer-top{flex-direction:column;}
}
</style>
</head>
<body>

<!-- Nav -->
<nav class="nav">
  <div class="nav-inner">
    <a href="/" class="logo">
      <svg width="28" height="28" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/>
        <circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/>
        <circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/>
        <path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/>
      </svg>
      <div>
        <div class="logo-text">Orbis <span>AI</span></div>
        <div class="logo-sub">Tennis &amp; Padel Intelligence</div>
      </div>
    </a>
    <div class="nav-links">
      <a href="#features" class="nav-link">Features</a>
      <a href="#why" class="nav-link">Why Orbis</a>
      <a href="/demo/coach" class="nav-link">Demo</a>
      <a href="/login" class="nav-link">Sign in</a>
      <a href="/waitlist" class="btn-waitlist">Join waiting list</a>
    </div>
  </div>
</nav>

<!-- Hero -->
<section class="hero">
  <div class="hero-badge">&#x1F3BE; For tennis &amp; padel coaches</div>
  <h1 class="hero-title">Stop losing students.<br><span class="accent">Start coaching smarter.</span></h1>
  <p class="hero-sub">Orbis AI is your AI-powered assistant coach — track every student, personalize every session, and never drop the ball on follow-up again.</p>
  <a href="#" <a class="btn-hero" href="/waitlist">Join waiting list &rarr;</a>
  <p class="hero-note">Free early access &middot; No credit card &middot; Limited spots</p>
</section>

<!-- Pain → Solution -->
<section class="pain-section">
  <div class="container">
    <div style="max-width:600px;">
      <div class="section-label">The problem</div>
      <h2 class="section-title">Great coaches lose students<br>to poor systems — not skill.</h2>
      <p class="section-sub">You know how to coach. But between managing schedules, chasing progress data, and trying to personalize 15 different students — the follow-up falls apart and students leave.</p>
    </div>
    <div class="pain-grid">
      <div class="pain-card">
        <div class="pain-icon purple">
          <svg viewBox="0 0 24 24" fill="none" stroke="#3d1a6e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
        <div class="pain-title">Students leave without warning</div>
        <div class="pain-desc">No system for tracking engagement, progress, or motivation drops. By the time you notice, they're gone.</div>
        <div class="pain-arrow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          Orbis tracks every student in real time
        </div>
      </div>
      <div class="pain-card">
        <div class="pain-icon amber">
          <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div class="pain-title">Hours lost to admin every week</div>
        <div class="pain-desc">WhatsApp, spreadsheets, PDFs, payment reminders. You became a coach, not a data entry operator.</div>
        <div class="pain-arrow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          Orbis automates the paperwork
        </div>
      </div>
      <div class="pain-card">
        <div class="pain-icon red">
          <svg viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="pain-title">No data to justify your sessions</div>
        <div class="pain-desc">Students ask "am I improving?" and you have nothing to show them. No progress data, no benchmarks, no evidence.</div>
        <div class="pain-arrow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          Orbis gives you AI-powered reports
        </div>
      </div>
      <div class="pain-card">
        <div class="pain-icon lime">
          <svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        </div>
        <div class="pain-title">Generic tools that don't get sport</div>
        <div class="pain-desc">Every existing tool was built for gym trainers. They don't speak ITF, FIP, padel tactics, or HRV. You're hacking workarounds daily.</div>
        <div class="pain-arrow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          Orbis was built for racket sports
        </div>
      </div>
    </div>
  </div>
</section>

<!-- Feature tabs -->
<section class="tabs-section" id="features">
  <div class="container">
    <div style="text-align:center;margin-bottom:40px;">
      <div class="section-label">Platform</div>
      <h2 class="section-title">Your assistant coach.<br>Always on. Always ready.</h2>
    </div>
    <div class="tabs">
      <div class="tab active" onclick="showTab('coaching')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
        Coach dashboard
      </div>
      <div class="tab" onclick="showTab('student')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        Student hub
      </div>
      <div class="tab" onclick="showTab('ai')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/></svg>
        Orbis Core AI
      </div>
      <div class="tab" onclick="showTab('video')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
        Video analysis
      </div>
    </div>

    <div id="tab-coaching" class="tab-content active">
      <div class="tab-text">
        <h3>Every student. Every session. Under control.</h3>
        <p>Your full roster in one place — with live recovery data, evaluation scores, progress trends, and AI-generated session plans. No more missed follow-ups.</p>
        <div class="tab-feats">
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Student roster with live Whoop recovery</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Coach + student dual evaluation forms</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>AI progress reports per student</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>ITF Level 1-3 + FIP Academy drill recommendations</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Session history and pattern detection</div>
        </div>
      </div>
      <div class="tab-visual">
        <div class="mock">
          <div class="mock-hdr"><div class="mock-hdr-title">Fernando · Jun 21</div><div class="mock-badge green">&#x1F7E2; Green zone</div></div>
          <div class="mock-row"><span>Recovery</span><span class="mock-val green">84%</span></div>
          <div class="mock-row"><span>HRV</span><span class="mock-val">57ms</span></div>
          <div class="mock-row"><span>Win rate</span><span class="mock-val">69%</span></div>
          <div class="mock-row"><span>Eval score</span><span class="mock-val">3.8 / 5</span></div>
          <div class="mock-bar-row">
            <div class="mock-bar-label"><span>Forehand</span><span style="font-weight:600;color:var(--navy);">4.2/5</span></div>
            <div class="mock-bar"><div class="mock-fill navy" style="width:84%"></div></div>
            <div class="mock-bar-label"><span>Backhand</span><span style="font-weight:600;color:var(--navy);">3.5/5</span></div>
            <div class="mock-bar"><div class="mock-fill navy" style="width:70%"></div></div>
            <div class="mock-bar-label"><span>Tactical</span><span style="font-weight:600;color:#f59e0b;">3.2/5 &#x26A0;</span></div>
            <div class="mock-bar"><div class="mock-fill amber" style="width:64%"></div></div>
          </div>
        </div>
      </div>
    </div>

    <div id="tab-student" class="tab-content">
      <div class="tab-text">
        <h3>Give every student their personal performance hub.</h3>
        <p>Students connect their wearables, upload documents, see their skill evolution, and chat with Orbis Core — all from their own dashboard. That's the personalization that keeps them coming back.</p>
        <div class="tab-feats">
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Whoop, Apple Health, Garmin, Fitbit</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Skill bars — coach vs self-assessment</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Document uploads — health, gym, nutrition plans</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Session history with coach notes</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Ask Orbis Core on Telegram anytime</div>
        </div>
      </div>
      <div class="tab-visual">
        <div class="mock">
          <div class="mock-hdr"><div class="mock-hdr-title">My devices</div><div class="mock-badge green">Whoop synced</div></div>
          <div class="mock-row"><span>Recovery</span><span class="mock-val green">84%</span></div>
          <div class="mock-row"><span>HRV</span><span class="mock-val">57ms &#x2197;</span></div>
          <div class="mock-row"><span>Sleep</span><span class="mock-val">7.4h</span></div>
          <div class="mock-row"><span>Resting HR</span><span class="mock-val">52 bpm</span></div>
          <div style="margin-top:14px;background:var(--bg);border-radius:8px;padding:11px 13px;font-size:12px;color:var(--text2);border-left:3px solid var(--lime);line-height:1.5;">
            <strong style="color:var(--lime-dark);">Orbis Core</strong> — Recovery 84%, HRV above baseline. Full intensity approved for today. Focus on backhand contact point.
          </div>
        </div>
      </div>
    </div>

    <div id="tab-ai" class="tab-content">
      <div class="tab-text">
        <h3>Your AI coaching brain — on Telegram.</h3>
        <p>Orbis Core is a role-aware AI agent grounded in ITF Level 1-3 and FIP Academy frameworks. Coaches and students get different, personalized intelligence. In English or Spanish. Always on.</p>
        <div class="tab-feats">
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>ITF Level 1-3 + FIP Academy Level 0-4 frameworks</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Daily briefing based on real Whoop data</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Drill suggestions from 9,500+ ATP matches</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Pre-match mental prep (APSQ psychology)</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Responds in English or Spanish</div>
        </div>
      </div>
      <div class="tab-visual">
        <div class="mock">
          <div class="mock-hdr"><div class="mock-hdr-title">Orbis Core · Telegram</div><div class="mock-badge purple">AI agent</div></div>
          <div class="chat-bubble user">Should Fernando train hard today?</div>
          <div class="chat-bubble ai">&#x1F7E2; Recovery 84% — green zone. HRV 57ms above his 55ms baseline. Full intensity approved. Focus backhand contact per ITF Level 2.</div>
          <div class="chat-bubble user">Which padel drill for net position?</div>
          <div class="chat-bubble ai">Chiquita drill: stand at T, feeder at net. Hit low passing shots at feet. 20min. FIP Academy Level 1 — net domination progression.</div>
        </div>
      </div>
    </div>

    <div id="tab-video" class="tab-content">
      <div class="tab-text">
        <h3>Frame-by-frame technique analysis.</h3>
        <p>Upload a session clip and Orbis Core analyzes contact point, footwork, hip rotation, and follow-through — with ITF and FIP drill recommendations grounded in the finding.</p>
        <div class="tab-feats">
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Visual annotations on frame snapshots</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Contact point, footwork, rotation breakdown</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>ITF + FIP drill recommendations per finding</div>
          <div class="tab-feat"><div class="tab-feat-check"><svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>Linked to student match stats and error patterns</div>
        </div>
        <a href="/demo/video" style="display:inline-flex;align-items:center;gap:6px;margin-top:20px;background:var(--navy);color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;">See live demo <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg></a>
      </div>
      <div class="tab-visual">
        <div style="position:relative;border-radius:12px;overflow:hidden;width:100%;box-shadow:0 8px 32px rgba(61,26,110,.15);">
          <img src="/static/forehand man.jpg" style="width:100%;display:block;max-height:280px;object-fit:cover;object-position:center top;" alt="Video analysis"/>
          <div style="position:absolute;top:10px;left:10px;background:rgba(61,26,110,.92);color:var(--lime);font-size:10px;font-weight:700;padding:4px 10px;border-radius:20px;">&#x2713; Orbis Core analyzed</div>
          <div style="position:absolute;top:38%;left:55%;width:52px;height:52px;border-radius:50%;border:2px dashed #f59e0b;"></div>
          <div style="position:absolute;top:33%;left:73%;background:rgba(61,26,110,.95);color:#f59e0b;font-size:9px;font-weight:700;padding:3px 8px;border-radius:4px;">&#x26A0; Contact late</div>
          <div style="position:absolute;bottom:10px;left:10px;background:rgba(0,0,0,.65);color:#fff;font-size:9px;padding:2px 7px;border-radius:3px;font-family:monospace;">00:14 / 01:23</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- Why Orbis -->
<section class="why-section" id="why">
  <div class="container">
    <div style="max-width:600px;margin-bottom:48px;">
      <div class="section-label">Why Orbis AI</div>
      <h2 class="section-title">Not a generic tool<br>with a tennis skin.</h2>
      <p class="section-sub">Every other platform was built for fitness coaches and adapted. Orbis was designed from day one for racket sports coaches.</p>
    </div>
    <!-- Photo row -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:48px;">
      <div style="border-radius:16px;overflow:hidden;height:320px;position:relative;">
        <img src="/static/Gemini_Generated_Image_b3exc0b3exc0b3ex.jpeg" style="width:100%;height:100%;object-fit:cover;object-position:center top;" alt="Tennis coach with Orbis Core"/>
        <div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(26,10,46,.8));padding:16px 20px;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--lime);margin-bottom:2px;">Tennis</div>
          <div style="font-size:14px;font-weight:600;color:#fff;">Real-time data review on court</div>
        </div>
      </div>
      <div style="border-radius:16px;overflow:hidden;height:320px;position:relative;">
        <img src="/static/Gemini_Generated_Image_qz6qanqz6qanqz6q.png" style="width:100%;height:100%;object-fit:cover;object-position:center top;" alt="Padel coach with Orbis Core"/>
        <div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(26,10,46,.8));padding:16px 20px;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--lime);margin-bottom:2px;">Padel</div>
          <div style="font-size:14px;font-weight:600;color:#fff;">AI coaching intelligence between sets</div>
        </div>
      </div>
    </div>

    <div class="why-grid">
      <div class="why-card">
        <div class="why-icon" style="background:rgba(61,26,110,.08);">
          <svg viewBox="0 0 24 24" fill="none" stroke="#3d1a6e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/></svg>
        </div>
        <div class="why-title">AI agent intelligence</div>
        <div class="why-desc">Orbis Core is a conversational AI agent that knows your students, reads their wearable data, and gives actionable recommendations — not generic tips.</div>
      </div>
      <div class="why-card">
        <div class="why-icon" style="background:var(--lime-pale);">
          <svg viewBox="0 0 24 24" fill="none" stroke="#2aad62" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        </div>
        <div class="why-title">Real ITF + FIP frameworks</div>
        <div class="why-desc">Every drill recommendation, session plan, and evaluation is grounded in ITF Level 1-3 (tennis) and FIP Academy Level 0-4 (padel) — not invented content.</div>
      </div>
      <div class="why-card">
        <div class="why-icon" style="background:#fef3c7;">
          <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
        </div>
        <div class="why-title">Psychology module (APSQ)</div>
        <div class="why-desc">Track pre-match anxiety, self-talk quality, and mental strain per student using the APSQ framework. See mental trends alongside physical performance.</div>
      </div>
      <div class="why-card">
        <div class="why-icon" style="background:#ede9fe;">
          <svg viewBox="0 0 24 24" fill="none" stroke="#6d28d9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </div>
        <div class="why-title">Wearable integration</div>
        <div class="why-desc">Whoop, Apple Health, Garmin and Fitbit connect directly. HRV, recovery, and sleep data inform every session recommendation automatically.</div>
      </div>
    </div>
  </div>
</section>

<!-- Comparison -->
<section class="comp-section">
  <div class="container">
    <div style="text-align:center;margin-bottom:48px;">
      <div style="background:rgba(62,207,126,.1);border:1px solid rgba(62,207,126,.2);border-radius:20px;padding:5px 14px;font-size:11px;color:var(--lime);font-weight:700;text-transform:uppercase;letter-spacing:.08em;display:inline-block;margin-bottom:14px;">Comparison</div>
      <h2 class="comp-title">Others manage fitness.<br>We coach tennis and padel.</h2>
      <p class="comp-sub">Every competitor solves operational problems. None solve coaching intelligence for racket sports.</p>
    </div>
    <div class="comp-table">
      <div class="comp-row hdr">
        <div class="comp-cell"><span class="comp-hdr">Feature</span></div>
        <div class="comp-cell"><span class="comp-hdr orbis">Orbis AI</span></div>
        <div class="comp-cell"><span class="comp-hdr">Others</span></div>
      </div>
      <div class="comp-row"><div class="comp-cell feat">Tennis-specific coaching tools</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
      <div class="comp-row"><div class="comp-cell feat">Padel coaching tools (FIP Academy)</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
      <div class="comp-row"><div class="comp-cell feat">ITF + FIP frameworks built-in</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
      <div class="comp-row"><div class="comp-cell feat">Wearable integration (HRV / recovery)</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
      <div class="comp-row"><div class="comp-cell feat">AI coaching agent on Telegram</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
      <div class="comp-row"><div class="comp-cell feat">ATP match benchmark comparisons</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
      <div class="comp-row"><div class="comp-cell feat">AI video analysis with annotations</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
      <div class="comp-row"><div class="comp-cell feat">Psychology tracking (APSQ)</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
      <div class="comp-row"><div class="comp-cell feat">Student dashboard + wearables</div><div class="comp-cell check-yes">&#x2713;</div><div class="comp-cell check-no">&#x2717;</div></div>
    </div>
  </div>
</section>

<!-- Footer -->
<footer class="footer">
  <div class="footer-inner">
    <div class="footer-top">
      <div class="footer-brand">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
          <svg width="22" height="22" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/><path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/></svg>
          <span style="font-size:15px;font-weight:700;color:#fff;">Orbis <span style="color:#3ecf7e;">AI</span></span>
        </div>
        <p>Tennis &amp; padel coaching intelligence. Built for coaches who want to win.</p>
      </div>
      <div class="footer-links">
        <div class="footer-col">
          <h4>Demo</h4>
          <a href="/demo/coach">Coach demo</a>
          <a href="/demo/student">Student demo</a>
          <a href="/demo/video">Video analysis</a>
        </div>
        <div class="footer-col">
          <h4>Platform</h4>
          <a href="/login">Sign in</a>
          <a href="/register">Register</a>
          <a href="https://t.me/orbiscoreai_bot" target="_blank">Orbis Core bot</a>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <p>&copy; 2026 Orbis AI. All rights reserved.</p>
      <p>Madrid, Spain · Tennis &amp; Padel Coaching Intelligence</p>
    </div>
  </div>
</footer>

<!-- Waitlist Modal -->
<div class="modal-overlay" id="modalOverlay" onclick="closeOnOverlay(event)">
  <div class="modal" style="position:relative;">
    <button class="modal-close" onclick="closeModal()">&#x2715;</button>
    <div id="modalForm">
      <div class="modal-logo">
        <svg width="24" height="24" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="4"/><circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="4"/><path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/></svg>
        <span style="font-size:15px;font-weight:700;color:var(--navy);">Orbis <span style="color:var(--lime-dark);">AI</span></span>
      </div>
      <h2 class="modal-title">Join the waiting list</h2>
      <p class="modal-sub">Be among the first coaches to get access. We're onboarding tennis and padel coaches in Europe and LatAm.</p>
      <div class="field"><label>Full name</label><input type="text" id="wl-name" placeholder="Toni Alcala" /></div>
      <div class="field"><label>Email</label><input type="email" id="wl-email" placeholder="toni@academy.com" /></div>
      <div class="field-row">
        <div class="field"><label>Country</label><input type="text" id="wl-country" placeholder="Spain" /></div>
        <div class="field"><label>City</label><input type="text" id="wl-city" placeholder="Madrid" /></div>
      </div>
      <div class="field">
        <label>Sport</label>
        <select id="wl-sport">
          <option value="tennis">Tennis</option>
          <option value="padel">Padel</option>
          <option value="both">Both tennis &amp; padel</option>
        </select>
      </div>
      <button class="btn-submit" id="wl-btn" onclick="submitWaitlist()">Join waiting list &#x2192;</button>
    </div>
    <div class="modal-success" id="modalSuccess" style="display:none;">
      <div class="check-big">&#x2705;</div>
      <h3 style="font-size:20px;font-weight:700;color:var(--text);margin-bottom:8px;">You're on the list!</h3>
      <p style="font-size:14px;color:var(--text2);line-height:1.6;">We'll reach out as soon as early access opens in your region. Thank you for joining Orbis AI.</p>
    </div>
  </div>
</div>

<script>
function showTab(id){
  document.querySelectorAll('.tab').forEach((t,i)=>{
    const ids=['coaching','student','ai','video'];
    t.classList.toggle('active',ids[i]===id);
  });
  document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
  document.getElementById('tab-'+id).classList.add('active');
}
function showModal(){document.getElementById("modalOverlay").classList.add("open");}
function openModal(){showModal();}

function closeModal(){document.getElementById('modalOverlay').classList.remove('open');}
function closeOnOverlay(e){if(e.target===document.getElementById('modalOverlay'))closeModal();}

async function submitWaitlist(){
  const name=document.getElementById('wl-name').value.trim();
  const email=document.getElementById('wl-email').value.trim();
  const country=document.getElementById('wl-country').value.trim();
  const city=document.getElementById('wl-city').value.trim();
  const sport=document.getElementById('wl-sport').value;
  if(!name||!email){alert('Please enter your name and email.');return;}
  const btn=document.getElementById('wl-btn');
  btn.disabled=true;btn.textContent='Saving...';
  try{
    const res=await fetch('/api/waitlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,email,country,city,sport})});
    if(res.ok){
      document.getElementById('modalForm').style.display='none';
      document.getElementById('modalSuccess').style.display='block';
    } else {
      btn.disabled=false;btn.textContent='Join waiting list \u2192';
      alert('Something went wrong. Please try again.');
    }
  }catch(e){
    btn.disabled=false;btn.textContent='Join waiting list \u2192';
    alert('Network error. Please try again.');
  }
}
</script>
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
.student-row{display:grid;grid-template-columns:auto 1fr auto auto auto auto;align-items:center;gap:14px;padding:13px 18px;border-bottom:.5px solid var(--border);transition:background .15s;}
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

</body>
</html>"""
SIMULATOR_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>Orbis AI — Padel Tactical Simulator</title>\n<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">\n<style>\n*{box-sizing:border-box;margin:0;padding:0;}\nhtml,body{height:100%;background:#f2f0f7;font-family:\'Inter\',system-ui,sans-serif;color:#1a0a2e;overflow:hidden;}\n.app{height:100vh;display:flex;flex-direction:column;background:#f2f0f7;}\n\n/* NAV */\n.nav{height:56px;background:#3d1a6e;border-bottom:1px solid rgba(255,255,255,.08);display:flex;align-items:center;justify-content:space-between;padding:0 20px;flex-shrink:0;box-shadow:0 2px 12px rgba(61,26,110,.2);}\n.nav-l{display:flex;align-items:center;gap:10px;}\n.logo{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:700;color:#fff;letter-spacing:-.02em;}\n.logo em{color:#3ecf7e;font-style:normal;}\n.ndiv{width:1px;height:16px;background:rgba(255,255,255,.18);}\n.nsub{font-size:11px;color:rgba(255,255,255,.55);font-weight:500;}\n.nav-r{display:flex;align-items:center;gap:8px;}\n.npill{background:rgba(62,207,126,.15);border:1px solid rgba(62,207,126,.3);border-radius:20px;padding:4px 11px;font-size:10.5px;font-weight:700;color:#3ecf7e;}\n.nbtn{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:8px;padding:6px 12px;font-size:10.5px;font-weight:600;color:rgba(255,255,255,.85);cursor:pointer;transition:background .15s;}\n.nbtn:hover{background:rgba(255,255,255,.18);}\n\n/* LEVEL BAR */\n.lbar{height:46px;background:#fff;border-bottom:1px solid #e2e6ef;display:flex;align-items:center;gap:6px;padding:0 20px;flex-shrink:0;}\n.lv{padding:5px 15px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;color:#9a8aaa;border:1px solid transparent;transition:all .2s;}\n.lv.lg{background:#d4f5e5;border-color:#9be8c4;color:#2aad62;}\n.lv.li{background:#fef3c7;border-color:#fcd989;color:#b45309;}\n.lv.lr{background:#fee2e2;border-color:#fca5a5;color:#b91c1c;}\n.lsep{flex:1;}\n.lcnt{font-size:11px;color:#9a8aaa;font-weight:600;}\n\n/* PLAY CHIPS */\n.pbar{background:#f2f0f7;border-bottom:1px solid #e2e6ef;padding:10px 20px;display:flex;gap:7px;overflow-x:auto;flex-shrink:0;scrollbar-width:none;}\n.pbar::-webkit-scrollbar{display:none;}\n.pc{padding:6px 14px;border-radius:8px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid #e2e6ef;background:#fff;color:#5a4a7a;white-space:nowrap;flex-shrink:0;transition:all .2s;}\n.pc:hover{border-color:#3d1a6e;}\n.pc.pca{background:#3d1a6e;border-color:#3d1a6e;color:#fff;}\n\n/* BODY */\n.body{display:grid;grid-template-columns:1fr 240px;flex:1;min-height:0;overflow:hidden;}\n\n/* COURT PANEL */\n.cpanel{background:#e8e4f0;display:flex;flex-direction:column;position:relative;overflow:hidden;}\n.cglow{position:absolute;inset:0;background:radial-gradient(ellipse 60% 40% at 50% 52%,rgba(61,26,110,.04) 0%,transparent 65%);pointer-events:none;}\n.cwrap{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;padding:18px 20px 6px;position:relative;}\n#court{display:block;max-width:100%;max-height:100%;}\n\n/* SHOT BAR */\n.shotbar{padding:9px 18px;display:flex;align-items:center;gap:9px;background:#fff;border-top:1px solid #e2e6ef;flex-shrink:0;}\n.sdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}\n.stxt{font-size:12.5px;font-weight:600;color:#3d2a5e;flex:1;}\n.sbadge{font-size:9.5px;font-weight:700;padding:3px 9px;border-radius:20px;}\n\n/* CONTROLS */\n.ctrl{background:#fff;border-top:1px solid #e2e6ef;padding:11px 20px;display:flex;align-items:center;gap:10px;flex-shrink:0;}\n.playbtn{width:38px;height:38px;border-radius:50%;background:#3ecf7e;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:transform .15s;box-shadow:0 2px 8px rgba(62,207,126,.35);}\n.playbtn:active{transform:scale(.92);}\n.playbtn svg{width:13px;height:13px;fill:#0a2a16;}\n.playbtn.playing svg{margin-left:0;}\n.ptrack{flex:1;height:4px;background:#e2e6ef;border-radius:3px;position:relative;cursor:pointer;}\n.pfill{height:100%;background:linear-gradient(90deg,#3ecf7e,#2aad62);border-radius:3px;width:0%;transition:none;}\n.pthumb{width:12px;height:12px;border-radius:50%;background:#3ecf7e;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.2);position:absolute;top:-4px;left:-6px;transition:none;}\n.pmeta{font-size:11px;color:#9a8aaa;font-weight:600;white-space:nowrap;}\n.cbtns{display:flex;gap:6px;}\n.cbtn{background:#f2f0f7;border:1px solid #e2e6ef;border-radius:7px;padding:6px 12px;font-size:11px;font-weight:600;color:#5a4a7a;cursor:pointer;transition:all .15s;}\n.cbtn:hover{background:#e8e4f0;color:#3d1a6e;}\n.cbtn.cg{background:#d4f5e5;border-color:#9be8c4;color:#2aad62;}\n\n/* RIGHT PANEL */\n.rp{background:#fff;border-left:1px solid #e2e6ef;display:flex;flex-direction:column;overflow:hidden;}\n.rps{padding:15px 16px;border-bottom:1px solid #e2e6ef;flex-shrink:0;}\n.rpl{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#9a8aaa;margin-bottom:7px;}\n.rpname{font-size:14px;font-weight:800;color:#1a0a2e;letter-spacing:-.01em;line-height:1.2;margin-bottom:6px;}\n.rptags{display:flex;gap:5px;margin-bottom:9px;flex-wrap:wrap;}\n.rptag{padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700;}\n.rpdesc{font-size:11px;color:#5a4a7a;line-height:1.65;}\n.rpseq{padding:11px 16px;flex:1;overflow-y:auto;scrollbar-width:none;}\n.rpseq::-webkit-scrollbar{display:none;}\n.seqi{display:flex;align-items:flex-start;gap:8px;padding:6px 7px;border-radius:7px;margin-bottom:2px;cursor:pointer;transition:background .15s;}\n.seqi.sa{background:#f0ebfa;}\n.seqn{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:9.5px;font-weight:700;flex-shrink:0;margin-top:1px;}\n.seqt{font-size:11px;color:#9a8aaa;line-height:1.45;padding-top:1px;}\n.seqi.sa .seqt{color:#3d1a6e;font-weight:600;}\n.seqw{font-size:9.5px;color:#d97706;font-weight:700;margin-top:1px;}\n.seqe{font-size:9.5px;color:#dc2626;font-weight:700;margin-top:1px;}\n.fip{padding:13px 16px;background:#f7f5fb;border-top:1px solid #e2e6ef;flex-shrink:0;}\n.fipl{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#7c4de0;margin-bottom:5px;display:flex;align-items:center;gap:4px;}\n.fipt{font-size:11px;color:#5a4a7a;line-height:1.6;font-style:italic;}\n</style>\n</head>\n<body>\n<div class="app">\n  <div class="nav">\n    <div class="nav-l">\n      <div class="logo">\n        <svg width="22" height="22" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="28" fill="none" stroke="#3ecf7e" stroke-width="3.5"/><circle cx="32" cy="32" r="19" fill="none" stroke="#3ecf7e" stroke-width="3.5"/><circle cx="32" cy="32" r="10" fill="none" stroke="#3ecf7e" stroke-width="3.5"/><path d="M32 20 L36 32 L32 44 L28 32 Z" fill="#3ecf7e"/></svg>\n        Orbis <em>AI</em>\n      </div>\n      <div class="ndiv"></div>\n      <div class="nsub">Padel tactical simulator · 2.5D</div>\n    </div>\n    <div class="nav-r">\n      <div class="npill">FIP Academy</div>\n      <div class="nbtn" onclick="openLibrary()">🔍 Browse +300 plays</div>\n      <div class="nbtn" onclick="window.location.href=\'/demo/coach\'">← Coach hub</div>\n    </div>\n  </div>\n\n  <div class="lbar">\n    <div class="lv lg" onclick="setLevel(0)" id="lv0">● Beginner</div>\n    <div class="lv" onclick="setLevel(1)" id="lv1">○ Intermediate</div>\n    <div class="lv" onclick="setLevel(2)" id="lv2">○ Advanced</div>\n    <div class="lsep"></div>\n    <div class="lcnt" id="lcnt">Play 1 of 6</div>\n  </div>\n\n  <div class="pbar" id="pbar"></div>\n\n  <div class="body">\n    <div class="cpanel">\n      <div class="cglow"></div>\n      <div class="cwrap">\n        <canvas id="court"></canvas>\n      </div>\n      <div class="shotbar">\n        <div class="sdot" id="sdot"></div>\n        <div class="stxt" id="stxt">Press Play to start</div>\n        <div class="sbadge" id="sbadge"></div>\n      </div>\n      <div class="ctrl">\n        <div style="display:flex;align-items:center;gap:10px;flex:1;">\n          <button class="playbtn" id="playbtn" onclick="togglePlay()">\n            <svg id="playicon" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg>\n          </button>\n          <div class="ptrack" id="ptrack">\n            <div class="pfill" id="pfill"></div>\n            <div class="pthumb" id="pthumb"></div>\n          </div>\n          <div class="pmeta" id="pmeta">— / —</div>\n        </div>\n        <div class="cbtns">\n          <div class="cbtn" onclick="prevShot()">← Prev</div>\n          <div class="cbtn" onclick="nextShot()">Next →</div>\n          <div class="cbtn cg" id="autobtn" onclick="toggleAuto()">▶ Auto</div>\n        </div>\n      </div>\n    </div>\n\n    <div class="rp">\n      <div class="rps">\n        <div class="rpl">Current play</div>\n        <div class="rpname" id="rpname">—</div>\n        <div class="rptags" id="rptags"></div>\n        <div class="rpdesc" id="rpdesc"></div>\n      </div>\n      <div class="rpseq" id="rpseq"></div>\n      <div class="fip">\n        <div class="fipl"><div style="width:4px;height:4px;border-radius:50%;background:#7c4de0;flex-shrink:0;"></div><span id="fiplvl">FIP Level 1</span></div>\n        <div class="fipt" id="fipt"></div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<script>\n// ── DATA ─────────────────────────────────────────────────────────────────────\nconst LEVELS=[\n{id:\'beginner\',label:\'Beginner\',dot:\'#4ade80\',cls:\'lg\',sym:\'●\',\nplays:[\n{name:\'Serve + net rush\',type:\'Offensive\',fip:\'FIP Level 1\',\ndesc:\'Serve down the T, both players sprint to net. Goal: own the net before opponents settle.\',\nfipText:\'In padel, the serve is a transition tool — the goal is to reach net, not win the point with the serve.\',\nsY:[{x:.32,y:.88},{x:.68,y:.88}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Serve down the T\',h:\'Y\',f:{x:.68,y:.88},c:{x:.5,y:.65},t:{x:.5,y:.12},ht:.15,d:1100,yP:[{x:.32,y:.88},{x:.68,y:.88}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Both sprint to net\',h:\'M\',f:{x:.5,y:.12},t:{x:.5,y:.12},ht:0,d:900,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents return cross-court\',h:\'O\',f:{x:.28,y:.14},c:{x:.55,y:.4},t:{x:.65,y:.62},ht:.1,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Volley winner — open court\',h:\'Y\',f:{x:.65,y:.6},c:{x:.4,y:.35},t:{x:.15,y:.1},ht:.05,d:750,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Lob + net rush\',type:\'Offensive\',fip:\'FIP Level 1\',\ndesc:\'Pinned at baseline, hit a deep lob over opponents and both sprint to net. Classic defensive-to-attack transition.\',\nfipText:\'The lob followed by net rush is the fundamental baseline-to-net transition. Time your sprint to the lob arc.\',\nsY:[{x:.32,y:.86},{x:.68,y:.86}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents drive at you\',h:\'O\',f:{x:.28,y:.14},c:{x:.4,y:.5},t:{x:.35,y:.82},ht:.05,d:900,yP:[{x:.32,y:.86},{x:.68,y:.86}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'LOB — deep over opponents\',h:\'Y\',f:{x:.35,y:.82},c:{x:.5,y:.22},t:{x:.5,y:.07},ht:.9,d:1800,yP:[{x:.32,y:.86},{x:.68,y:.86}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Sprint to net — both players\',h:\'M\',f:{x:.5,y:.07},t:{x:.5,y:.07},ht:0,d:900,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.07},{x:.72,y:.07}]},\n{l:\'Opponents scramble — weak reply\',h:\'O\',f:{x:.5,y:.07},c:{x:.45,y:.35},t:{x:.42,y:.62},ht:.2,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.07},{x:.72,y:.07}]},\n{l:\'Volley winner\',h:\'Y\',f:{x:.42,y:.6},c:{x:.5,y:.32},t:{x:.5,y:.08},ht:.05,d:750,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.07},{x:.72,y:.07}],w:true}\n]},\n{name:\'Deep cross-court lob\',type:\'Defensive\',fip:\'FIP Level 1\',\ndesc:\'From baseline, lob cross-court to the deepest corner. Opponent must travel maximum distance.\',\nfipText:\'Always lob cross-court and deep. A short lob is punished; a deep cross-court lob forces maximum opponent movement.\',\nsY:[{x:.32,y:.84},{x:.68,y:.84}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents drive to your left\',h:\'O\',f:{x:.72,y:.14},c:{x:.45,y:.5},t:{x:.32,y:.8},ht:.08,d:950,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Deep cross-court LOB\',h:\'Y\',f:{x:.32,y:.8},c:{x:.72,y:.3},t:{x:.85,y:.07},ht:.85,d:1900,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponent forced back — weak overhead\',h:\'O\',f:{x:.85,y:.07},c:{x:.6,y:.4},t:{x:.55,y:.8},ht:.2,d:1100,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.85,y:.08},{x:.45,y:.14}]},\n{l:\'LOB again — deep parallel\',h:\'Y\',f:{x:.55,y:.8},c:{x:.55,y:.35},t:{x:.82,y:.07},ht:.8,d:1700,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.85,y:.08},{x:.45,y:.14}]}\n]},\n{name:\'Middle volley attack\',type:\'Offensive\',fip:\'FIP Level 1\',\ndesc:\'Both players at net attack consecutively down the middle corridor between opponents.\',\nfipText:\'The middle is the most dangerous zone in padel. Neither opponent has clear authority — attack it consistently.\',\nsY:[{x:.32,y:.57},{x:.68,y:.57}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents play cross-court ball\',h:\'O\',f:{x:.28,y:.14},c:{x:.55,y:.38},t:{x:.65,y:.62},ht:.08,d:950,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'First volley — down the middle\',h:\'Y\',f:{x:.65,y:.6},c:{x:.5,y:.38},t:{x:.5,y:.16},ht:.05,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents weak central reply\',h:\'O\',f:{x:.5,y:.16},c:{x:.5,y:.4},t:{x:.5,y:.65},ht:.15,d:900,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'VOLLEY WINNER — middle\',h:\'Y\',f:{x:.5,y:.62},c:{x:.5,y:.38},t:{x:.5,y:.12},ht:.04,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Defensive lob rotation\',type:\'Defensive\',fip:\'FIP Level 1\',\ndesc:\'Both players rotate lobs patiently from baseline. Alternate cross-court and parallel. Wait for errors.\',\nfipText:\'Patient baseline defense wins points at beginner level. Opponents will make overhead errors if you keep the ball deep and vary direction.\',\nsY:[{x:.32,y:.84},{x:.68,y:.84}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents smash from net\',h:\'O\',f:{x:.32,y:.14},c:{x:.4,y:.5},t:{x:.36,y:.82},ht:.05,d:800,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Cross-court LOB — deep right\',h:\'Y\',f:{x:.36,y:.82},c:{x:.72,y:.32},t:{x:.82,y:.07},ht:.82,d:1800,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents bandeja back center\',h:\'O\',f:{x:.82,y:.07},c:{x:.5,y:.38},t:{x:.45,y:.84},ht:.2,d:1100,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Parallel LOB — down the line\',h:\'Y\',f:{x:.45,y:.84},c:{x:.45,y:.38},t:{x:.75,y:.07},ht:.8,d:1700,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Overhead error — point won!\',h:\'O\',f:{x:.75,y:.07},c:{x:.6,y:.5},t:{x:.95,y:.95},ht:.05,d:800,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}],e:true}\n]},\n{name:\'Recovery lob\',type:\'Defensive\',fip:\'FIP Level 1\',\ndesc:\'Under pressure with no time to construct — play a high defensive lob to buy time and reset.\',\nfipText:\'When in doubt — LOB. The globo always gives you time to recover position and restart the point from neutral.\',\nsY:[{x:.32,y:.82},{x:.68,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Hard drive at body — no time\',h:\'O\',f:{x:.5,y:.14},c:{x:.5,y:.5},t:{x:.5,y:.78},ht:.04,d:750,yP:[{x:.32,y:.82},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'RECOVERY LOB — high and deep\',h:\'Y\',f:{x:.5,y:.78},c:{x:.35,y:.25},t:{x:.28,y:.07},ht:.9,d:1900,yP:[{x:.32,y:.82},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Reposition at baseline\',h:\'M\',f:{x:.28,y:.07},t:{x:.28,y:.07},ht:0,d:700,yP:[{x:.3,y:.84},{x:.7,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents bandeja — controlled\',h:\'O\',f:{x:.28,y:.07},c:{x:.45,y:.38},t:{x:.48,y:.82},ht:.18,d:1100,yP:[{x:.3,y:.84},{x:.7,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Cross-court LOB — now in control\',h:\'Y\',f:{x:.48,y:.82},c:{x:.75,y:.3},t:{x:.85,y:.07},ht:.82,d:1700,yP:[{x:.3,y:.84},{x:.7,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]}\n]}\n]},\n{id:\'intermediate\',label:\'Intermediate\',dot:\'#fbbf24\',cls:\'li\',sym:\'○\',\nplays:[\n{name:\'Chiquita + advance\',type:\'Neutral\',fip:\'FIP Level 2\',\ndesc:\'Play a chiquita at the net player\\\'s feet, then immediately advance to net. The chiquita is a transition shot — always follow it.\',\nfipText:\'FIP Level 2: The chiquita is a transition shot — if you don\\\'t follow it to net, you\\\'ve wasted it. Always advance after the chiquita.\',\nsY:[{x:.3,y:.74},{x:.7,y:.74}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents attack — fast low ball\',h:\'O\',f:{x:.28,y:.14},c:{x:.35,y:.5},t:{x:.35,y:.7},ht:.04,d:850,yP:[{x:.3,y:.74},{x:.7,y:.74}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'CHIQUITA — low at net player\\\'s feet\',h:\'Y\',f:{x:.35,y:.7},c:{x:.32,y:.52},t:{x:.3,y:.3},ht:.04,d:900,yP:[{x:.3,y:.74},{x:.7,y:.74}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Advance to net — both players\',h:\'M\',f:{x:.3,y:.3},t:{x:.3,y:.3},ht:0,d:800,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Forced volley up — weak reply\',h:\'O\',f:{x:.28,y:.18},c:{x:.48,y:.4},t:{x:.52,y:.65},ht:.3,d:1100,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'CROSS VOLLEY WINNER\',h:\'Y\',f:{x:.52,y:.62},c:{x:.72,y:.35},t:{x:.88,y:.1},ht:.06,d:700,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Lob + chiquita mix\',type:\'Neutral\',fip:\'FIP Level 2\',\ndesc:\'Alternate lobs and chiquitas — never two consecutive lobs. Keeps net players constantly repositioning.\',\nfipText:\'FIP Level 2: Lob + chiquita alternation is the most important pattern for baseline players. Predictable defense is exploitable.\',\nsY:[{x:.3,y:.82},{x:.7,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents drive at you\',h:\'O\',f:{x:.5,y:.14},c:{x:.5,y:.5},t:{x:.5,y:.78},ht:.06,d:900,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'LOB — push opponents back\',h:\'Y\',f:{x:.5,y:.78},c:{x:.5,y:.3},t:{x:.5,y:.08},ht:.85,d:1800,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Bandeja — coming forward again\',h:\'O\',f:{x:.5,y:.08},c:{x:.5,y:.38},t:{x:.5,y:.78},ht:.2,d:1100,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.16}]},\n{l:\'CHIQUITA — catches them mid-court\',h:\'Y\',f:{x:.5,y:.78},c:{x:.5,y:.58},t:{x:.5,y:.38},ht:.04,d:850,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.16}]},\n{l:\'Advance to net\',h:\'M\',f:{x:.5,y:.38},t:{x:.5,y:.38},ht:0,d:750,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.16},{x:.7,y:.16}]},\n{l:\'Weak reply from opponents\',h:\'O\',f:{x:.3,y:.2},c:{x:.45,y:.4},t:{x:.45,y:.65},ht:.25,d:1000,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.16},{x:.7,y:.16}]},\n{l:\'VOLLEY WINNER\',h:\'Y\',f:{x:.45,y:.62},c:{x:.5,y:.35},t:{x:.85,y:.08},ht:.05,d:700,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.16},{x:.7,y:.16}],w:true}\n]},\n{name:\'Bandeja hold at net\',type:\'Neutral\',fip:\'FIP Level 2\',\ndesc:\'When lobbed, play a bandeja (tray shot) wide to the glass to maintain net position rather than attacking.\',\nfipText:\'FIP Level 2: The bandeja is THE signature padel shot. Its goal is not to win — it\\\'s to hold net position and force another lob.\',\nsY:[{x:.32,y:.57},{x:.68,y:.57}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'You attack — cross-court volley\',h:\'Y\',f:{x:.32,y:.57},c:{x:.55,y:.35},t:{x:.72,y:.12},ht:.05,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents LOB over your head\',h:\'O\',f:{x:.72,y:.12},c:{x:.5,y:.4},t:{x:.5,y:.76},ht:.82,d:1800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Right player drops back\',h:\'M\',f:{x:.5,y:.76},t:{x:.5,y:.76},ht:0,d:600,yP:[{x:.32,y:.57},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'BANDEJA — wide to side glass\',h:\'Y\',f:{x:.68,y:.76},c:{x:.88,y:.45},t:{x:.92,y:.12},ht:.12,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Recover to net\',h:\'M\',f:{x:.92,y:.12},t:{x:.92,y:.12},ht:0,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents LOB again\',h:\'O\',f:{x:.92,y:.12},c:{x:.6,y:.38},t:{x:.45,y:.78},ht:.78,d:1700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'SECOND BANDEJA — holding net\',h:\'Y\',f:{x:.45,y:.74},c:{x:.3,y:.45},t:{x:.15,y:.12},ht:.12,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]}\n]},\n{name:\'Vibora cross-court\',type:\'Offensive\',fip:\'FIP Level 2-3\',\ndesc:\'High ball at center court — attack with a vibora (viper shot) with sidespin to the far side glass.\',\nfipText:\'FIP Level 2-3: Cross-court vibora angles the ball into the corner after the glass — the standard professional direction for this shot.\',\nsY:[{x:.28,y:.64},{x:.68,y:.62}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'You drive cross-court\',h:\'Y\',f:{x:.28,y:.64},c:{x:.6,y:.42},t:{x:.72,y:.12},ht:.15,d:1000,yP:[{x:.28,y:.64},{x:.68,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents LOB back — high center\',h:\'O\',f:{x:.72,y:.12},c:{x:.58,y:.4},t:{x:.65,y:.58},ht:.8,d:1700,yP:[{x:.28,y:.64},{x:.68,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'VIBORA — cutting to side glass\',h:\'Y\',f:{x:.65,y:.56},c:{x:.95,y:.35},t:{x:.97,y:.09},ht:.08,d:700,yP:[{x:.28,y:.64},{x:.68,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Chiquita + lob rotation\',type:\'Defensive\',fip:\'FIP Level 2\',\ndesc:\'Alternate lob and chiquita — never predictable. Forces net players to constantly adjust their feet.\',\nfipText:\'FIP Level 2: Directional and tactical variety prevents opponents from pre-positioning. Two consecutive lobs of the same type are always exploitable.\',\nsY:[{x:.3,y:.82},{x:.7,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents push — hard flat drive\',h:\'O\',f:{x:.72,y:.14},c:{x:.55,y:.5},t:{x:.58,y:.8},ht:.04,d:800,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'LOB #1 — parallel deep\',h:\'Y\',f:{x:.58,y:.8},c:{x:.6,y:.35},t:{x:.78,y:.07},ht:.82,d:1700,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Bandeja — coming forward\',h:\'O\',f:{x:.78,y:.07},c:{x:.55,y:.38},t:{x:.52,y:.8},ht:.18,d:1100,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.14}]},\n{l:\'CHIQUITA — catches them moving in\',h:\'Y\',f:{x:.52,y:.8},c:{x:.48,y:.6},t:{x:.46,y:.36},ht:.04,d:850,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.14}]},\n{l:\'Weak volley up from net player\',h:\'O\',f:{x:.3,y:.2},c:{x:.45,y:.44},t:{x:.5,y:.78},ht:.35,d:1100,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.14}]},\n{l:\'LOB #2 — cross-court deep\',h:\'Y\',f:{x:.5,y:.78},c:{x:.78,y:.3},t:{x:.85,y:.07},ht:.8,d:1700,yP:[{x:.3,y:.82},{x:.7,y:.82}],oP:[{x:.3,y:.16},{x:.7,y:.14}]}\n]},\n{name:\'Drive + net rush\',type:\'Offensive\',fip:\'FIP Level 2\',\ndesc:\'When opponents are slightly off net, strike a low flat drive at their feet then sprint to net behind the shot.\',\nfipText:\'FIP Level 2: The drive is underused in modern padel. When opponents are out of position, a flat drive + rush is more direct than a chiquita.\',\nsY:[{x:.3,y:.76},{x:.7,y:.76}],sO:[{x:.3,y:.18},{x:.7,y:.18}],\nshots:[\n{l:\'Opponents slightly off net\',h:\'O\',f:{x:.3,y:.18},c:{x:.45,y:.5},t:{x:.42,y:.74},ht:.06,d:900,yP:[{x:.3,y:.76},{x:.7,y:.76}],oP:[{x:.3,y:.18},{x:.7,y:.18}]},\n{l:\'DRIVE — flat low at their feet\',h:\'Y\',f:{x:.42,y:.74},c:{x:.35,y:.52},t:{x:.3,y:.32},ht:.03,d:800,yP:[{x:.3,y:.76},{x:.7,y:.76}],oP:[{x:.3,y:.18},{x:.7,y:.18}]},\n{l:\'Sprint to net behind the drive\',h:\'M\',f:{x:.3,y:.32},t:{x:.3,y:.32},ht:0,d:800,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.18}]},\n{l:\'Forced weak low volley reply\',h:\'O\',f:{x:.3,y:.22},c:{x:.45,y:.42},t:{x:.5,y:.65},ht:.3,d:1000,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.18}]},\n{l:\'PARALLEL VOLLEY WINNER\',h:\'Y\',f:{x:.5,y:.62},c:{x:.35,y:.38},t:{x:.12,y:.1},ht:.05,d:700,yP:[{x:.3,y:.57},{x:.7,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.18}],w:true}\n]}\n]},\n{id:\'advanced\',label:\'Advanced\',dot:\'#f87171\',cls:\'lr\',sym:\'○\',\nplays:[\n{name:\'Full point pattern — pro\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Complete professional sequence: serve → approach volley → bandeja → chiquita pressure → vibora winner. Five-shot architecture.\',\nfipText:\'FIP Level 3: Point construction patterns — pre-planned 5-shot sequences — are how professional pairs approach every point systematically.\',\nsY:[{x:.32,y:.88},{x:.68,y:.88}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'(1) Body serve to weaker player\',h:\'Y\',f:{x:.68,y:.88},c:{x:.35,y:.65},t:{x:.28,y:.12},ht:.15,d:1000,yP:[{x:.32,y:.88},{x:.68,y:.88}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Rush to net\',h:\'M\',f:{x:.28,y:.12},t:{x:.28,y:.12},ht:0,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(2) Opponent lobs — deep\',h:\'O\',f:{x:.28,y:.14},c:{x:.5,y:.35},t:{x:.5,y:.72},ht:.78,d:1700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(3) BANDEJA — hold net position\',h:\'Y\',f:{x:.5,y:.68},c:{x:.75,y:.42},t:{x:.88,y:.1},ht:.12,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Recover to net\',h:\'M\',f:{x:.88,y:.1},t:{x:.88,y:.1},ht:0,d:600,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(4) Opponents push flat drive\',h:\'O\',f:{x:.88,y:.1},c:{x:.6,y:.42},t:{x:.55,y:.62},ht:.05,d:850,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(5) VIBORA — cutting winner\',h:\'Y\',f:{x:.55,y:.6},c:{x:.95,y:.35},t:{x:.97,y:.09},ht:.08,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Vibora to side glass\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Hit vibora with sidespin into the side glass — ball bounces at a sharp low angle opponents cannot reach.\',\nfipText:\'FIP Level 3: Vibora into the side glass is the professional standard winner. The ball dies in a zone opponents cannot position for.\',\nsY:[{x:.28,y:.62},{x:.7,y:.6}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Rally — drive cross-court\',h:\'Y\',f:{x:.28,y:.62},c:{x:.6,y:.4},t:{x:.72,y:.12},ht:.12,d:1000,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents LOB — high ball center\',h:\'O\',f:{x:.72,y:.12},c:{x:.58,y:.38},t:{x:.62,y:.56},ht:.82,d:1700,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'VIBORA — to side glass parallel\',h:\'Y\',f:{x:.62,y:.54},c:{x:.97,y:.4},t:{x:.97,y:.1},ht:.07,d:700,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Ball dies off glass — point won\',h:\'Y\',f:{x:.97,y:.1},c:{x:.8,y:.15},t:{x:.65,y:.22},ht:0,d:600,yP:[{x:.28,y:.62},{x:.7,y:.6}],oP:[{x:.72,y:.14},{x:.88,y:.22}],w:true}\n]},\n{name:\'Bajada — aggressive wall exit\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Take overhead off the back glass early on the way down — hit flat with forward pressure rather than waiting.\',\nfipText:\'FIP Level 3: The bajada is taken early on the way down from the glass — high risk, high reward. Only when the ball is cleanly above you.\',\nsY:[{x:.32,y:.57},{x:.68,y:.57}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents LOB — deep to back glass\',h:\'O\',f:{x:.5,y:.14},c:{x:.5,y:.45},t:{x:.5,y:.84},ht:.88,d:1900,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Drop back to intercept\',h:\'M\',f:{x:.5,y:.84},t:{x:.5,y:.84},ht:0,d:600,yP:[{x:.32,y:.78},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'BAJADA — take early off glass\',h:\'Y\',f:{x:.5,y:.82},c:{x:.5,y:.55},t:{x:.5,y:.12},ht:.25,d:1100,yP:[{x:.32,y:.78},{x:.68,y:.78}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Recover to net\',h:\'M\',f:{x:.5,y:.12},t:{x:.5,y:.12},ht:0,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents scramble — weak reply\',h:\'O\',f:{x:.5,y:.12},c:{x:.48,y:.4},t:{x:.45,y:.65},ht:.2,d:1000,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'FINISH — volley winner\',h:\'Y\',f:{x:.45,y:.62},c:{x:.5,y:.35},t:{x:.5,y:.1},ht:.04,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Defense → lob → chiquita → net\',type:\'Neutral\',fip:\'FIP Level 3\',\ndesc:\'Three-shot conversion: lob for time → chiquita for pressure → advance to net and finish. The pro defensive-to-attack sequence.\',\nfipText:\'FIP Level 3: The three-touch net takeover is the benchmark advanced pattern. Each shot has a specific purpose — time, pressure, position.\',\nsY:[{x:.32,y:.84},{x:.68,y:.84}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents smash hard\',h:\'O\',f:{x:.5,y:.14},c:{x:.5,y:.5},t:{x:.5,y:.8},ht:.04,d:750,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'(1) LOB — create time\',h:\'Y\',f:{x:.5,y:.8},c:{x:.38,y:.28},t:{x:.28,y:.08},ht:.88,d:1900,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponents bandeja coming forward\',h:\'O\',f:{x:.28,y:.08},c:{x:.48,y:.4},t:{x:.48,y:.82},ht:.2,d:1100,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.3,y:.18},{x:.7,y:.14}]},\n{l:\'(2) CHIQUITA — pressure at feet\',h:\'Y\',f:{x:.48,y:.82},c:{x:.42,y:.62},t:{x:.38,y:.36},ht:.04,d:900,yP:[{x:.32,y:.84},{x:.68,y:.84}],oP:[{x:.3,y:.18},{x:.7,y:.14}]},\n{l:\'(3) Advance to net — both\',h:\'M\',f:{x:.38,y:.36},t:{x:.38,y:.36},ht:0,d:800,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.14}]},\n{l:\'Forced weak volley from net player\',h:\'O\',f:{x:.3,y:.22},c:{x:.48,y:.42},t:{x:.52,y:.68},ht:.32,d:1100,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.14}]},\n{l:\'NET WINNER — cross volley\',h:\'Y\',f:{x:.52,y:.65},c:{x:.72,y:.38},t:{x:.88,y:.1},ht:.05,d:700,yP:[{x:.32,y:.57},{x:.68,y:.57}],oP:[{x:.3,y:.18},{x:.7,y:.14}],w:true}\n]},\n{name:\'Around the post\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Cornered wide at side glass with a low ball — hit it around the net post rather than over. 100% legal.\',\nfipText:\'FIP Level 3: Around-the-post (por el palo) is legal in padel and occasionally used by professionals when the angle makes it the optimal shot.\',\nsY:[{x:.3,y:.82},{x:.68,y:.82}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Opponents angle vibora — wide left\',h:\'O\',f:{x:.32,y:.14},c:{x:.1,y:.45},t:{x:.06,y:.74},ht:.08,d:900,yP:[{x:.3,y:.82},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Chase to far left wall\',h:\'M\',f:{x:.06,y:.74},t:{x:.06,y:.74},ht:0,d:600,yP:[{x:.06,y:.75},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'AROUND THE POST — por el palo!\',h:\'Y\',f:{x:.06,y:.74},c:{x:-.02,y:.52},t:{x:.08,y:.2},ht:.04,d:950,yP:[{x:.06,y:.75},{x:.68,y:.82}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]},\n{name:\'Australian + switch\',type:\'Offensive\',fip:\'FIP Level 3\',\ndesc:\'Both line up same side before serve. Net player crosses to opposite side immediately as serve lands — misdirection.\',\nfipText:\'FIP Level 3: Australian formation misdirection gives the serving pair a tactical advantage on the first volley by confusing the receiver\\\'s read.\',\nsY:[{x:.55,y:.88},{x:.55,y:.72}],sO:[{x:.28,y:.14},{x:.72,y:.14}],\nshots:[\n{l:\'Australian — both left side\',h:\'M\',f:{x:.55,y:.72},t:{x:.55,y:.72},ht:0,d:400,yP:[{x:.55,y:.88},{x:.55,y:.72}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Serve wide right\',h:\'Y\',f:{x:.55,y:.88},c:{x:.72,y:.62},t:{x:.72,y:.12},ht:.15,d:1000,yP:[{x:.55,y:.88},{x:.55,y:.72}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Net player SWITCHES to right\',h:\'M\',f:{x:.72,y:.12},t:{x:.72,y:.12},ht:0,d:700,yP:[{x:.35,y:.62},{x:.72,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Opponent confused — cross return\',h:\'O\',f:{x:.72,y:.12},c:{x:.42,y:.4},t:{x:.32,y:.65},ht:.1,d:1000,yP:[{x:.35,y:.62},{x:.72,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}]},\n{l:\'Left player intercepts — WINNER\',h:\'Y\',f:{x:.32,y:.63},c:{x:.5,y:.38},t:{x:.88,y:.1},ht:.05,d:750,yP:[{x:.35,y:.62},{x:.72,y:.62}],oP:[{x:.28,y:.14},{x:.72,y:.14}],w:true}\n]}\n]}\n];\n\n// ── STATE ─────────────────────────────────────────────────────────────────────\nlet lvl=0,play=0,shot=0,playing=false;\nlet animId=null,autoTimer=null,shotStart=null,shotT=0;\n\nfunction getPlay(){return LEVELS[lvl].plays[play];}\nfunction getShots(){return getPlay().shots;}\n\n// ── CANVAS SETUP ──────────────────────────────────────────────────────────────\nconst canvas=document.getElementById(\'court\');\nlet CW,CH,ML,MR,MT,MB,CX,CY,CW2,CH2;\n\nfunction setupCanvas(){\n  const wrap=document.querySelector(\'.cwrap\');\n  const W=wrap.clientWidth,H=wrap.clientHeight;\n  // 2.5D court: perspective quad\n  // wider at bottom, narrower at top\n  // We need space for perspective + glass walls\n  const cH=Math.max(200,Math.min(H-10,W*1.3));\n  const cW=Math.max(160,Math.min(W-10,cH/1.3));\n  const dpr=window.devicePixelRatio||1;\n  canvas.width=cW*dpr;canvas.height=cH*dpr;\n  canvas.style.width=cW+\'px\';\n  canvas.style.height=cH+\'px\';\n  canvas.getContext(\'2d\').setTransform(dpr,0,0,dpr,0,0);\n  CW=cW;CH=cH;\n  // Perspective court corners:\n  // TL=(CW*0.22,CH*0.06) TR=(CW*0.78,CH*0.06)\n  // BL=(CW*0.04,CH*0.94) BR=(CW*0.96,CH*0.94)\n}\n\n// Convert normalized padel coords to perspective screen coords\n// x: 0=left, 1=right; y: 0=top (opponents back), 1=bottom (your back)\nfunction toScreen(nx,ny){\n  // Interpolate between top edge and bottom edge\n  const topL={x:CW*0.22,y:CH*0.055};\n  const topR={x:CW*0.78,y:CH*0.055};\n  const botL={x:CW*0.04,y:CH*0.945};\n  const botR={x:CW*0.96,y:CH*0.945};\n  const lx=topL.x+(botL.x-topL.x)*ny;\n  const ly=topL.y+(botL.y-topL.y)*ny;\n  const rx=topR.x+(botR.x-topR.x)*ny;\n  const ry=topR.y+(botR.y-topR.y)*ny;\n  return{x:lx+(rx-lx)*nx,y:ly+(ry-ly)*nx+(ry-ly)*0};\n}\n// Actually simpler — for a trapezoid:\nfunction sc(nx,ny){\n  const tLx=CW*0.22,tLy=CH*0.055,tRx=CW*0.78,tRy=CH*0.055;\n  const bLx=CW*0.04,bLy=CH*0.945,bRx=CW*0.96,bRy=CH*0.945;\n  const lx=tLx+(bLx-tLx)*ny, ly=tLy+(bLy-tLy)*ny;\n  const rx=tRx+(bRx-tRx)*ny, ry=tRy+(bRy-tRy)*ny;\n  const sx=lx+(rx-lx)*nx, sy=ly+(ry-ly)*nx + (ry-ly)*(0);\n  // Y pos is purely based on ny for the trapezoid:\n  const px=lx+(rx-lx)*nx;\n  const py=tLy+(bLy-tLy)*ny;\n  return{x:px,y:py};\n}\n\nfunction lerp(a,b,t){return a+(b-a)*t;}\nfunction ease(t){return t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;}\nfunction bez(p0,p1,p2,t){\n  return{x:(1-t)*(1-t)*p0.x+2*(1-t)*t*p1.x+t*t*p2.x,\n         y:(1-t)*(1-t)*p0.y+2*(1-t)*t*p1.y+t*t*p2.y};\n}\n\n// ── DRAW ─────────────────────────────────────────────────────────────────────\nfunction drawCourt(ctx){\n  const tL=sc(0,0),tR=sc(1,0),bL=sc(0,1),bR=sc(1,1);\n  const tLx=CW*0.22,tRx=CW*0.78,tY=CH*0.055;\n  const bLx=CW*0.04,bRx=CW*0.96,bY=CH*0.945;\n\n  // Background\n  ctx.fillStyle=\'#1a4d7a\';ctx.fillRect(0,0,CW,CH);\n\n  // Ground glow\n  const grd=ctx.createRadialGradient(CW/2,CH*0.55,0,CW/2,CH*0.55,CW*0.5);\n  grd.addColorStop(0,\'rgba(120,180,255,0.1)\');grd.addColorStop(1,\'rgba(0,0,0,0)\');\n  ctx.fillStyle=grd;ctx.fillRect(0,0,CW,CH);\n\n  // Glass wall — back (top strip)\n  ctx.beginPath();ctx.moveTo(tLx-CW*0.04,tY-CH*0.045);ctx.lineTo(tRx+CW*0.04,tY-CH*0.045);ctx.lineTo(tRx,tY);ctx.lineTo(tLx,tY);ctx.closePath();\n  ctx.fillStyle=\'rgba(200,230,255,0.14)\';ctx.fill();\n  ctx.strokeStyle=\'rgba(200,230,255,0.5)\';ctx.lineWidth=1.5;ctx.stroke();\n\n  // Glass wall — left side\n  ctx.beginPath();ctx.moveTo(tLx-CW*0.04,tY-CH*0.045);ctx.lineTo(tLx,tY);ctx.lineTo(bLx,bY);ctx.lineTo(bLx-CW*0.04,bY+CH*0.035);ctx.closePath();\n  ctx.fillStyle=\'rgba(200,230,255,0.08)\';ctx.fill();\n  ctx.strokeStyle=\'rgba(200,230,255,0.35)\';ctx.lineWidth=1.2;ctx.stroke();\n\n  // Glass wall — right side\n  ctx.beginPath();ctx.moveTo(tRx+CW*0.04,tY-CH*0.045);ctx.lineTo(tRx,tY);ctx.lineTo(bRx,bY);ctx.lineTo(bRx+CW*0.04,bY+CH*0.035);ctx.closePath();\n  ctx.fillStyle=\'rgba(200,230,255,0.08)\';ctx.fill();\n  ctx.strokeStyle=\'rgba(200,230,255,0.35)\';ctx.lineWidth=1.2;ctx.stroke();\n\n  // Court surface — padel blue\n  ctx.beginPath();ctx.moveTo(tLx,tY);ctx.lineTo(tRx,tY);ctx.lineTo(bRx,bY);ctx.lineTo(bLx,bY);ctx.closePath();\n  ctx.fillStyle=\'#2e6cb0\';ctx.fill();\n\n  // Subtle horizontal lines (floor texture)\n  for(let i=1;i<9;i++){\n    const t=i/9;\n    const lx=tLx+(bLx-tLx)*t,rx=tRx+(bRx-tRx)*t,y=tY+(bY-tY)*t;\n    ctx.beginPath();ctx.moveTo(lx,y);ctx.lineTo(rx,y);\n    ctx.strokeStyle=\'rgba(255,255,255,0.045)\';ctx.lineWidth=0.8;ctx.stroke();\n  }\n\n  // Court boundary — bold white frame (matches official court markings)\n  ctx.beginPath();ctx.moveTo(tLx,tY);ctx.lineTo(tRx,tY);ctx.lineTo(bRx,bY);ctx.lineTo(bLx,bY);ctx.closePath();\n  ctx.strokeStyle=\'rgba(255,255,255,0.92)\';ctx.lineWidth=3;ctx.stroke();\n\n  // Net (at y=0.5)\n  const nL=sc(0,0.5),nR=sc(1,0.5);\n  // Net shadow\n  ctx.beginPath();ctx.moveTo(nL.x,nL.y+3);ctx.lineTo(nR.x,nR.y+3);\n  ctx.strokeStyle=\'rgba(0,0,0,0.35)\';ctx.lineWidth=6;ctx.stroke();\n  // Net surface\n  ctx.beginPath();ctx.moveTo(nL.x,nL.y);ctx.lineTo(nR.x,nR.y);\n  ctx.strokeStyle=\'rgba(255,255,255,0.95)\';ctx.lineWidth=4;ctx.stroke();\n  // Net mesh\n  const nSteps=18;\n  for(let i=0;i<=nSteps;i++){\n    const nx=nL.x+(nR.x-nL.x)*(i/nSteps);\n    const ny=nL.y+(nR.y-nL.y)*(i/nSteps);\n    ctx.beginPath();ctx.moveTo(nx,ny-5);ctx.lineTo(nx,ny+5);\n    ctx.strokeStyle=\'rgba(255,255,255,0.18)\';ctx.lineWidth=0.7;ctx.stroke();\n  }\n  // Net posts\n  const postH=CH*0.04;\n  ctx.fillStyle=\'rgba(230,230,240,0.85)\';\n  ctx.fillRect(nL.x-4,nL.y-postH,6,postH*1.8);\n  ctx.fillRect(nR.x-2,nR.y-postH,6,postH*1.8);\n\n  // Service lines — real padel dimension: 7m from net on a 10m half-court (y=0.5 ± 0.35)\n  const sL1=sc(0,0.15),sR1=sc(1,0.15);\n  const sL2=sc(0,0.85),sR2=sc(1,0.85);\n  ctx.strokeStyle=\'rgba(255,255,255,0.55)\';ctx.lineWidth=2;ctx.setLineDash([]);\n  ctx.beginPath();ctx.moveTo(sL1.x,sL1.y);ctx.lineTo(sR1.x,sR1.y);ctx.stroke();\n  ctx.beginPath();ctx.moveTo(sL2.x,sL2.y);ctx.lineTo(sR2.x,sR2.y);ctx.stroke();\n\n  // Center lines — only within service boxes (between net and service line), matching real court markings\n  const cN=sc(.5,.5),cS1=sc(.5,.15),cS2=sc(.5,.85);\n  ctx.strokeStyle=\'rgba(255,255,255,0.45)\';ctx.lineWidth=1.6;\n  ctx.beginPath();ctx.moveTo(cS1.x,cS1.y);ctx.lineTo(cN.x,cN.y);ctx.stroke();\n  ctx.beginPath();ctx.moveTo(cN.x,cN.y);ctx.lineTo(cS2.x,cS2.y);ctx.stroke();\n\n  // Zone labels\n  ctx.fillStyle=\'rgba(255,255,255,0.1)\';ctx.font=`bold ${Math.round(CW*0.022)}px Inter,sans-serif`;ctx.textAlign=\'center\';\n  const topC=sc(.5,.07);ctx.fillText(\'OPPONENTS\',topC.x,topC.y);\n  const botC=sc(.5,.93);ctx.fillText(\'YOUR TEAM\',botC.x,botC.y);\n\n  // Wall labels\n  ctx.fillStyle=\'rgba(200,230,255,0.4)\';ctx.font=`${Math.round(CW*0.018)}px Inter,sans-serif`;\n  const topMid=sc(.5,.02);ctx.fillText(\'BACK WALL\',topMid.x,topMid.y+2);\n  const botMid=sc(.5,.98);ctx.fillText(\'BACK WALL\',botMid.x,botMid.y-2);\n\n  // NET label\n  ctx.fillStyle=\'rgba(255,255,255,0.35)\';ctx.font=`bold ${Math.round(CW*0.016)}px Inter,sans-serif`;ctx.textAlign=\'left\';\n  ctx.fillText(\'NET\',nR.x+CW*0.02,nR.y+4);\n}\n\nfunction playerSize(ny){\n  // Players further away (small ny = top = far) appear smaller in perspective\n  return Math.round(CW*(0.028+ny*0.022));\n}\n\nfunction drawPlayer(ctx,nx,ny,fill,ring,label,active){\n  const p=sc(nx,ny);\n  const r=playerSize(ny);\n  const bodyH=r*1.6;\n  // Shadow\n  ctx.beginPath();ctx.ellipse(p.x,p.y+r*0.25,r*0.9,r*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=\'rgba(0,0,0,0.45)\';ctx.fill();\n  // Body cylinder (side faces as trapezoid for perspective)\n  ctx.beginPath();\n  ctx.moveTo(p.x-r,p.y);ctx.lineTo(p.x+r,p.y);\n  ctx.lineTo(p.x+r*0.9,p.y-bodyH);ctx.lineTo(p.x-r*0.9,p.y-bodyH);\n  ctx.closePath();\n  ctx.fillStyle=fill;ctx.fill();\n  // Top disc\n  ctx.beginPath();ctx.ellipse(p.x,p.y-bodyH,r*0.9,r*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=ring;ctx.fill();\n  ctx.strokeStyle=ring;ctx.lineWidth=active?2.5:2;ctx.stroke();\n  // Active pulse\n  if(active){\n    ctx.beginPath();ctx.ellipse(p.x,p.y-bodyH,r*1.3,r*0.46,0,0,Math.PI*2);\n    ctx.strokeStyle=\'rgba(62,207,126,0.3)\';ctx.lineWidth=1.5;ctx.stroke();\n    ctx.beginPath();ctx.ellipse(p.x,p.y,r*1.1,r*0.4,0,0,Math.PI*2);\n    ctx.fillStyle=\'rgba(62,207,126,0.06)\';ctx.fill();\n  }\n  // Label on top disc\n  ctx.fillStyle=\'rgba(255,255,255,0.95)\';\n  ctx.font=`bold ${Math.round(r*0.75)}px Inter,sans-serif`;\n  ctx.textAlign=\'center\';ctx.textBaseline=\'middle\';\n  ctx.fillText(label,p.x,p.y-bodyH+r*0.08);\n}\n\nfunction drawArrow(ctx,x1,y1,x2,y2,col){\n  const a=Math.atan2(y2-y1,x2-x1),l=10;\n  ctx.strokeStyle=col;ctx.lineWidth=1.8;ctx.setLineDash([]);\n  ctx.beginPath();ctx.moveTo(x2,y2);\n  ctx.lineTo(x2-l*Math.cos(a-.42),y2-l*Math.sin(a-.42));\n  ctx.moveTo(x2,y2);\n  ctx.lineTo(x2-l*Math.cos(a+.42),y2-l*Math.sin(a+.42));\n  ctx.stroke();\n}\n\nfunction drawBall(ctx,nx,ny,h){\n  const p=sc(nx,ny);\n  const pr=playerSize(ny);\n  const lift=h*CH*0.12;\n  const r=pr*0.45+h*pr*0.35;\n  // Shadow (on court surface — at p.y, not lifted)\n  const sScale=Math.max(0.3,1-h*0.5);\n  ctx.beginPath();ctx.ellipse(p.x,p.y,r*sScale*0.9,r*sScale*0.32,0,0,Math.PI*2);\n  ctx.fillStyle=`rgba(0,0,0,${0.38-h*0.18})`;ctx.fill();\n  // Glow aura when high\n  if(h>0.3){\n    ctx.beginPath();ctx.arc(p.x,p.y-lift,r*2,0,Math.PI*2);\n    ctx.fillStyle=`rgba(212,232,10,${h*0.06})`;ctx.fill();\n  }\n  // Ball body\n  ctx.beginPath();ctx.arc(p.x,p.y-lift,r,0,Math.PI*2);\n  ctx.fillStyle=\'#d4e820\';ctx.fill();\n  ctx.strokeStyle=\'#9aac00\';ctx.lineWidth=1.2;ctx.stroke();\n  // Seam\n  ctx.strokeStyle=\'rgba(255,255,255,0.3)\';ctx.lineWidth=0.9;\n  ctx.beginPath();ctx.arc(p.x,p.y-lift,r,0.3,Math.PI-0.3);ctx.stroke();\n  ctx.beginPath();ctx.arc(p.x,p.y-lift,r,Math.PI+0.3,2*Math.PI-0.3);ctx.stroke();\n  // Highlight\n  ctx.beginPath();ctx.arc(p.x-r*0.28,p.y-lift-r*0.28,r*0.28,0,Math.PI*2);\n  ctx.fillStyle=\'rgba(255,255,255,0.32)\';ctx.fill();\n}\n\nfunction drawTrail(ctx,s,alpha){\n  if(s.h===\'M\')return;\n  const f=sc(s.f.x,s.f.y);\n  const c=s.c?sc(s.c.x,s.c.y):sc((s.f.x+s.t.x)/2,(s.f.y+s.t.y)/2);\n  const t=sc(s.t.x,s.t.y);\n  ctx.beginPath();ctx.moveTo(f.x,f.y);ctx.quadraticCurveTo(c.x,c.y,t.x,t.y);\n  const col=s.h===\'Y\'?`rgba(245,158,11,${alpha})`:`rgba(248,113,113,${alpha})`;\n  ctx.strokeStyle=col;ctx.lineWidth=1.8;ctx.setLineDash([7,5]);ctx.stroke();ctx.setLineDash([]);\n  // Arrowhead\n  const e1=bez(s.f,s.c||{x:(s.f.x+s.t.x)/2,y:(s.f.y+s.t.y)/2},s.t,0.98);\n  const e2=bez(s.f,s.c||{x:(s.f.x+s.t.x)/2,y:(s.f.y+s.t.y)/2},s.t,0.92);\n  const p1=sc(e1.x,e1.y),p2=sc(e2.x,e2.y);\n  drawArrow(ctx,p2.x,p2.y,p1.x,p1.y,col.replace(/[\\d.]+\\)$/,\'0.75)\'));\n}\n\nfunction drawMoveArrows(ctx,s,prevY,curY){\n  if(s.h!==\'M\')return;\n  prevY.forEach((prev,i)=>{\n    const cur=curY[i];\n    if(Math.abs(prev.x-cur.x)<0.01&&Math.abs(prev.y-cur.y)<0.01)return;\n    const f=sc(prev.x,prev.y),t=sc(cur.x,cur.y);\n    ctx.beginPath();ctx.moveTo(f.x,f.y);ctx.lineTo(t.x,t.y);\n    ctx.strokeStyle=\'rgba(167,139,250,0.65)\';ctx.lineWidth=1.8;ctx.setLineDash([5,4]);ctx.stroke();ctx.setLineDash([]);\n    drawArrow(ctx,f.x,f.y,t.x,t.y,\'rgba(167,139,250,0.65)\');\n  });\n}\n\nfunction render(bt){\n  const ctx=canvas.getContext(\'2d\');\n  ctx.clearRect(0,0,CW,CH);\n  const p=getPlay();const shots=p.shots;const et=ease(Math.min(bt??1,1));\n\n  drawCourt(ctx);\n\n  // Past trails\n  for(let i=0;i<shot;i++)drawTrail(ctx,shots[i],0.14);\n  if(shot<shots.length)drawTrail(ctx,shots[shot],0.32);\n\n  // Player positions\n  const s=shots[Math.min(shot,shots.length-1)];\n  const prevY=shot===0?p.sY:(shots[shot-1].yP||p.sY);\n  const prevO=shot===0?p.sO:(shots[shot-1].oP||p.sO);\n  const curY=s.yP||prevY;const curO=s.oP||prevO;\n\n  const py=curY.map((q,i)=>({x:lerp(prevY[i].x,q.x,et),y:lerp(prevY[i].y,q.y,et)}));\n  const po=curO.map((q,i)=>({x:lerp(prevO[i].x,q.x,et),y:lerp(prevO[i].y,q.y,et)}));\n\n  // Move arrows\n  drawMoveArrows(ctx,s,prevY,curY);\n\n  // Draw opponents first (behind net = further = drawn first)\n  po.forEach((q,i)=>drawPlayer(ctx,q.x,q.y,\'#50000e\',\'#dc2626\',[\'O1\',\'O2\'][i],false));\n\n  // Draw your team (in front)\n  py.forEach((q,i)=>drawPlayer(ctx,q.x,q.y,\'#1a0a2e\',i===1?\'#3ecf7e\':\'#7c4de0\',[\'Y1\',\'Y2\'][i],i===1&&s.h===\'M\'));\n\n  // Ball\n  if(shot<shots.length&&s.h!==\'M\'){\n    const f=s.f,c=s.c||{x:(s.f.x+s.t.x)/2,y:(s.f.y+s.t.y)/2},t2=s.t;\n    const bp=bez(f,c,t2,et);\n    const h=(s.ht||0)*Math.sin(et*Math.PI);\n    drawBall(ctx,bp.x,bp.y,h);\n  } else {\n    // Show ball at rest at last position\n    const last=shots[Math.min(shot===shots.length?shot-1:Math.max(shot-1,0),shots.length-1)];\n    if(last)drawBall(ctx,last.t.x,last.t.y,0);\n  }\n\n  // Step badge\n  const total=shots.length;const cur=Math.min(shot+1,total);\n  const badgeText=`Shot ${cur} / ${total}`;\n  ctx.font=`600 ${Math.round(CW*0.018)}px Inter,sans-serif`;\n  const textW=ctx.measureText(badgeText).width;\n  const padX=CW*0.018;\n  const badgeW=textW+padX*2;\n  const badgeH=CH*0.038;\n  const badgeX=CW-badgeW-CW*0.025;\n  const badgeY=CH*0.02;\n  ctx.fillStyle=\'rgba(61,26,110,0.88)\';\n  ctx.beginPath();if(ctx.roundRect)ctx.roundRect(badgeX,badgeY,badgeW,badgeH,badgeH/2);else ctx.rect(badgeX,badgeY,badgeW,badgeH);\n  ctx.fill();\n  ctx.fillStyle=\'rgba(255,255,255,0.9)\';ctx.textAlign=\'center\';\n  ctx.fillText(badgeText,badgeX+badgeW/2,badgeY+badgeH*0.68);\n}\n\n// ── ANIMATION ─────────────────────────────────────────────────────────────────\nfunction animFrame(ts){\n  const s=getShots()[shot];\n  if(!shotStart)shotStart=ts;\n  const t=Math.min((ts-shotStart)/s.d,1);\n  render(t);\n  // Progress\n  const total=getShots().reduce((a,x)=>a+x.d,0);\n  const done=getShots().slice(0,shot).reduce((a,x)=>a+x.d,0)+(ts-shotStart);\n  updateProgress(Math.min(done/total,1));\n  updateShotList(shot);\n  updateShotBar(shot);\n  if(t>=1){\n    shot++;\n    if(shot>=getShots().length){\n      // Done\n      playing=false;\n      document.getElementById(\'playicon\').innerHTML=\'<polygon points="5,3 19,12 5,21"/>\';\n      document.getElementById(\'playbtn\').classList.remove(\'playing\');\n      render(1);updateProgress(1);updateShotList(getShots().length-1);\n      if(autoOn){\n        autoTimer=setTimeout(()=>{\n          shot=0;shotStart=null;\n          if(play<LEVELS[lvl].plays.length-1){play++;loadPlay(play);}\n          else{stopAuto();}\n        },1200);\n      }\n      return;\n    }\n    shotStart=null;\n  }\n  if(playing)animId=requestAnimationFrame(animFrame);\n}\n\nfunction togglePlay(){\n  if(playing){\n    playing=false;if(animId)cancelAnimationFrame(animId);\n    document.getElementById(\'playicon\').innerHTML=\'<polygon points="5,3 19,12 5,21"/>\';\n  } else {\n    if(shot>=getShots().length){shot=0;shotStart=null;updateProgress(0);}\n    playing=true;shotStart=null;\n    document.getElementById(\'playicon\').innerHTML=\'<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>\';\n    document.getElementById(\'playbtn\').classList.add(\'playing\');\n    animId=requestAnimationFrame(animFrame);\n  }\n}\n\nfunction nextShot(){\n  stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);\n  if(shot<getShots().length-1){shot++;render(1);updateShotList(shot);updateShotBar(shot);}\n}\nfunction prevShot(){\n  stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);\n  if(shot>0){shot--;render(1);updateShotList(shot);updateShotBar(shot);}\n}\n\nlet autoOn=false;\nfunction toggleAuto(){\n  if(autoOn){stopAuto();return;}\n  autoOn=true;document.getElementById(\'autobtn\').textContent=\'■ Stop\';\n  shot=0;shotStart=null;updateProgress(0);\n  if(!playing)togglePlay();\n}\nfunction stopAuto(){\n  autoOn=false;document.getElementById(\'autobtn\').textContent=\'▶ Auto\';\n  if(autoTimer){clearTimeout(autoTimer);autoTimer=null;}\n}\n\n// ── UI ────────────────────────────────────────────────────────────────────────\nfunction updateProgress(t){\n  const pct=(t*100).toFixed(1)+\'%\';\n  document.getElementById(\'pfill\').style.width=pct;\n  document.getElementById(\'pthumb\').style.left=`calc(${pct} - 5px)`;\n  const cur=Math.min(shot+1,getShots().length);\n  document.getElementById(\'pmeta\').textContent=`${cur} / ${getShots().length} shots`;\n}\n\nfunction updateShotBar(idx){\n  const s=getShots()[Math.min(idx,getShots().length-1)];\n  if(!s)return;\n  const dot=document.getElementById(\'sdot\');\n  const txt=document.getElementById(\'stxt\');\n  const badge=document.getElementById(\'sbadge\');\n  const col=s.h===\'M\'?\'#a78bfa\':s.h===\'Y\'?\'#f59e0b\':\'#f87171\';\n  dot.style.background=col;\n  txt.textContent=s.l+(s.w?\' ★\':\'\')+(s.e?\' ✗\':\'\');\n  if(s.h===\'M\'){badge.textContent=\'Move\';badge.style.background=\'rgba(167,139,250,.12)\';badge.style.color=\'#a78bfa\';badge.style.border=\'1px solid rgba(167,139,250,.25)\';}\n  else if(s.w){badge.textContent=\'Winner ★\';badge.style.background=\'rgba(245,158,11,.12)\';badge.style.color=\'#f59e0b\';badge.style.border=\'1px solid rgba(245,158,11,.25)\';}\n  else if(s.e){badge.textContent=\'Error ✗\';badge.style.background=\'rgba(248,113,113,.1)\';badge.style.color=\'#f87171\';badge.style.border=\'1px solid rgba(248,113,113,.25)\';}\n  else{badge.textContent=s.h===\'Y\'?\'Your shot\':\'Opp. shot\';badge.style.background=s.h===\'Y\'?\'rgba(245,158,11,.1)\':\'rgba(248,113,113,.08)\';badge.style.color=col;badge.style.border=`1px solid ${col}44`;}\n}\n\nfunction updateShotList(active){\n  const list=document.getElementById(\'rpseq\');\n  list.innerHTML=\'\';\n  const shots=getShots();\n  shots.forEach((s,i)=>{\n    const d=document.createElement(\'div\');\n    d.className=\'seqi\'+(i===active?\' sa\':\'\');\n    d.onclick=()=>{stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);shot=i;render(1);updateShotList(i);updateShotBar(i);};\n    const col=s.h===\'M\'?\'rgba(167,139,250,.12)\':s.h===\'Y\'?\'rgba(245,158,11,.12)\':\'rgba(248,113,113,.1)\';\n    const tcol=s.h===\'M\'?\'#a78bfa\':s.h===\'Y\'?\'#f59e0b\':\'#f87171\';\n    d.innerHTML=`<div class="seqn" style="background:${i===active?tcol:col};color:${i===active?\'#000\':tcol};">${i+1}</div>`+\n      `<div><div class="seqt">${s.l}</div>${s.w?\'<div class="seqw">★ Point won</div>\':\'\'}${s.e?\'<div class="seqe">✗ Error</div>\':\'\'}</div>`;\n    list.appendChild(d);\n  });\n}\n\nfunction buildPlaybar(){\n  const row=document.getElementById(\'pbar\');\n  row.innerHTML=\'\';\n  LEVELS[lvl].plays.forEach((p,i)=>{\n    const d=document.createElement(\'div\');\n    d.className=\'pc\'+(i===play?\' pca\':\'\');\n    d.textContent=`${i+1} · ${p.name}`;\n    d.onclick=()=>loadPlay(i);\n    row.appendChild(d);\n  });\n}\n\nfunction loadPlay(idx){\n  stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);\n  play=idx;shot=0;shotStart=null;\n  document.getElementById(\'playicon\').innerHTML=\'<polygon points="5,3 19,12 5,21"/>\';\n  document.getElementById(\'playbtn\').classList.remove(\'playing\');\n  updateProgress(0);\n  buildPlaybar();\n  const p=getPlay();\n  document.getElementById(\'rpname\').textContent=p.name;\n  document.getElementById(\'lcnt\').textContent=`Play ${idx+1} of ${LEVELS[lvl].plays.length}`;\n  // Tags\n  const tc=p.type===\'Offensive\'?[\'rgba(62,207,126,.1)\',\'#3ecf7e\',\'rgba(62,207,126,.18)\']:p.type===\'Defensive\'?[\'rgba(251,191,36,.08)\',\'#fbbf24\',\'rgba(251,191,36,.2)\']:[\'rgba(147,197,253,.08)\',\'#93c5fd\',\'rgba(147,197,253,.2)\'];\n  const lc=LEVELS[lvl];\n  document.getElementById(\'rptags\').innerHTML=\n    `<span class="rptag" style="background:${tc[0]};color:${tc[1]};border:1px solid ${tc[2]};">${p.type}</span>`+\n    `<span class="rptag" style="background:#f7f5fb;color:${lc.dot};border:1px solid ${lc.dot}55;">${lc.label}</span>`;\n  document.getElementById(\'rpdesc\').textContent=p.desc;\n  document.getElementById(\'fiplvl\').textContent=p.fip;\n  document.getElementById(\'fipt\').textContent=p.fipText;\n  updateShotList(0);updateShotBar(0);\n  render(1);\n}\n\nfunction setLevel(l){\n  stopAuto();playing=false;if(animId)cancelAnimationFrame(animId);\n  lvl=l;play=0;shot=0;shotStart=null;\n  [\'lv0\',\'lv1\',\'lv2\'].forEach((id,i)=>{\n    const el=document.getElementById(id);\n    el.className=\'lv\';\n    if(i===l){el.classList.add(LEVELS[l].cls);el.textContent=LEVELS[l].sym+\' \'+LEVELS[l].label;}\n    else{el.textContent=\'○ \'+LEVELS[i].label;}\n  });\n  buildPlaybar();loadPlay(0);\n}\n\n// INIT\nwindow.addEventListener(\'resize\',()=>{setupCanvas();render(1);});\nrequestAnimationFrame(()=>{\n  setupCanvas();\n  setLevel(0);\n});\n</script>\n\n<div id="libraryModal" style="display:none;position:fixed;inset:0;background:rgba(26,10,46,.45);backdrop-filter:blur(4px);z-index:999;align-items:center;justify-content:center;padding:20px;">\n  <div style="background:#fff;border:1px solid #e2e6ef;border-radius:16px;max-width:520px;width:100%;max-height:80vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(61,26,110,.25);">\n    <div style="padding:18px 20px;border-bottom:1px solid #e2e6ef;display:flex;align-items:center;justify-content:space-between;">\n      <div>\n        <div style="font-size:15px;font-weight:800;color:#1a0a2e;">Padel Plays Library</div>\n        <div style="font-size:11px;color:#9a8aaa;margin-top:2px;">+300 plays &middot; FIP Academy framework</div>\n      </div>\n      <div onclick="closeLibrary()" style="cursor:pointer;color:#9a8aaa;font-size:18px;line-height:1;">✕</div>\n    </div>\n    <div style="padding:14px 20px;border-bottom:1px solid #e2e6ef;">\n      <input type="text" placeholder="Search plays, shots, tactics..." style="width:100%;background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:9px 12px;font-size:12.5px;color:#1a0a2e;outline:none;font-family:inherit;">\n    </div>\n    <div style="padding:16px 20px;overflow-y:auto;">\n      <div style="font-size:11px;font-weight:700;color:#9a8aaa;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">Available now — 18 plays</div>\n      <div style="font-size:12px;color:#5a4a7a;line-height:1.7;margin-bottom:16px;">These are fully animated and ready to demo. Select a level above to explore them.</div>\n      <div style="font-size:11px;font-weight:700;color:#9a8aaa;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">Coming soon — 282 more plays</div>\n      <div style="display:flex;flex-direction:column;gap:6px;">\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Serve plays &middot; 24 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Net domination &middot; 38 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Wall plays &middot; 52 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Defensive plays &middot; 44 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Smash &amp; overhead plays &middot; 36 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Passing shots &middot; 28 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Point construction &middot; 36 more</div>\n        <div style="background:#f2f0f7;border:1px solid #e2e6ef;border-radius:8px;padding:8px 12px;font-size:11.5px;color:#5a4a7a;">Special &amp; trick plays &middot; 24 more</div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<script>\nfunction openLibrary(){document.getElementById(\'libraryModal\').style.display=\'flex\';}\nfunction closeLibrary(){document.getElementById(\'libraryModal\').style.display=\'none\';}\n</script>\n</body>\n</html>\n'

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

from mangum import Mangum
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
