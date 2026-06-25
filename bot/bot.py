import os
import logging
import anthropic
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

KNOWLEDGE_BASE = """
=== ORBIS CORE KNOWLEDGE BASE ===

--- ITF COACHING FRAMEWORKS (Level 1-3) ---

ITF Level 1 — Foundation:
- Rally consistency is the primary objective at beginner-intermediate level
- Groundstroke technique: unit turn, split step, contact point in front of body
- Serve fundamentals: trophy position, pronation, leg drive
- Court positioning: base position 1m behind baseline center
- Key principle: Reduce unforced errors before adding winners

ITF Level 2 — Development:
- Tactical patterns: cross-court rally as neutral, down-the-line as attacking
- Backhand slice: defensive reset tool, low contact point, open face
- Serve + 1: serve wide to open court, attack with forehand inside-out
- Net approach: split step before volley, angle volley away from opponent
- Point construction: build point from baseline, attack short ball
- Physical: periodization — hard/medium/easy week rotation

ITF Level 3 — Performance:
- Match analysis: first serve % target 63%+, unforced errors below 20/match
- Tactical adaptation: identify opponent weakness in first 3 games
- Mental performance: pre-point routine (bounce ball, breath, focus word)
- Physical: HRV-guided training load — reduce intensity if HRV drops >10% from baseline
- Recovery: 48h between high-intensity sessions, sleep 7-9h minimum

--- FIP PADEL COACHING GUIDELINES ---

Padel fundamentals:
- The wall is your ally — use it for defense and counter-attack
- Service: underarm only, bounce then hit, must land in diagonal service box
- Bandeja: overhead with slice spin used to maintain net position
- Vibora: aggressive overhead with topspin used to finish points
- Lob: primary defensive weapon — aim for back corners
- Key positions: net (attacking), back (defensive)

Padel tactics:
- Net position wins matches — team that controls net wins 70%+ of points
- Attack through the middle: reduces opponents angle options
- Chiquita: low passing shot at net players feet — main counter to net dominance
- Golden rule: never lob short — always aim past service line
- Rotation: both players move together — never split the pair

Padel mental game:
- Points are short — reset between each point is critical
- Mistakes come in clusters — break the pattern with a timeout or lob

--- SPORTS SCIENCE — HRV & LOAD MANAGEMENT ---

HRV interpretation:
- Male age 35 baseline: 55ms (Fernando baseline)
- Green zone: HRV >60ms — full training approved
- Amber zone: HRV 45-60ms — moderate intensity, no new maximal efforts
- Red zone: HRV <45ms — recovery session only, no match play
- Trend matters more than single day: 3-day declining trend = load reduction

Recovery science:
- Sleep <7h reduces reaction time 3% per hour below threshold
- Sleep <6h increases injury risk 1.7x
- Optimal acute:chronic workload ratio: 0.8-1.3
- Heat/humidity: add 0.5L hydration per hour of play above 25°C
- 48h minimum between high-intensity sessions

Training load guidance by recovery score:
- Recovery 80%+: High intensity approved — technical + tactical + physical
- Recovery 65-79%: Medium intensity — technical focus, reduce physical load 20%
- Recovery 50-64%: Low intensity only — skill work, no match play
- Recovery <50%: Rest or active recovery only — walking, mobility

--- ATP BENCHMARKS (9,500+ matches) ---

ATP Tour averages:
- First serve %: 63% (Fernando target: 60%)
- First serve points won: 74.5%
- Second serve points won: 55.2%
- Aces per match: 8.2
- Double faults per match: 3.1
- Winners per player per match: 28.4
- Unforced errors per player per match: 21.8
- Rally length average: 4.1 shots
- Net points won: 67.3%

Advanced recreational benchmarks (Fernando's level):
- First serve %: 58%
- Winners per match: 12
- Unforced errors per match: 22
- Win rate vs similar level: 50%
- Average match duration: 85 min

--- FERNANDO'S REAL DATA (Demo Player) ---

Profile:
- Name: Fernando de los Rios
- Age: 35, Peruvian, right-handed
- Level: Advanced recreational, clay specialist
- Academy: Roger Lederer Academy, Coach Toni Alcala
- Madrid, Spain

Current performance (real Whoop data):
- Today recovery: 84% — GREEN zone
- Today HRV: 57ms (baseline 55ms — above baseline)
- Today sleep: 7.4h
- Resting HR: 52 bpm
- 7-day avg recovery: 76%
- 7-day avg HRV: 54ms
- 3-day trend: STABLE-IMPROVING

Recent session history:
- Jun 21: Recovery 84% — Rest day
- Jun 20: Recovery 80% — Serve and volley drills, 90 min
- Jun 17: Recovery 85% — Match play vs James, Won 6-3 6-4
- Jun 15: Recovery 81% — Evaluation session, full skill assessment
- Jun 14: Recovery 64% — Light walking only (below threshold)
- Jun 13: Recovery 69% — Weightlifting 68min RPE 4
- Jun 12: Recovery 82% — Rest

Match performance (real data):
- Matches played: 7
- Win rate: 69% (above 50% recreational benchmark)
- First serve %: 58% (target: 60%)
- Winners per match: 12 (vs 28.4 ATP avg)
- Unforced errors: 22 per match (target: below 18)
- Avg match duration: 85 min
- Recovery-win correlation: 75% win rate when recovery >80%, 40% when <65%

Skill evaluation (Coach Toni, Jun 15):
- Forehand: 4.2/5 (coach) / 4.0/5 (self) — STRENGTH
- Backhand: 3.5/5 (coach) / 3.2/5 (self) — MAIN GAP
- Serve: 3.8/5 (coach) / 4.0/5 (self) — solid, room to improve
- Movement: 4.0/5 (coach) / 3.8/5 (self) — good
- Tactical: 3.2/5 (coach) / 3.0/5 (self) — KEY IMPROVEMENT AREA

Psychology (APSQ):
- Latest score: 1.29/5 average — LOW strain
- Pre-match anxiety: 2.8/10 (manageable)
- Self-talk quality: 8.1/10 (excellent)
- Goal clarity: 8.0/10
- Previous week had shoulder worry and higher anxiety (6.6/10) — improved significantly
- Coach notes: Pre-competition anxiety manageable

Fernando's key development priorities:
1. Backhand under pressure — highest leverage technical gap (3.5/5)
2. Tactical point construction — build patterns from baseline (3.2/5)
3. First serve consistency — target 60% (currently 58%)
4. Unforced error reduction — target below 18/match (currently 22)

Next session (Jun 26, Thursday 10am):
- Focus: Backhand slice as defensive reset + serve consistency drills
- Recovery: 84% — full intensity approved

=== END KNOWLEDGE BASE ===
"""

COACH_SYSTEM = f"""You are Orbis Core, the AI coaching intelligence for Orbis AI — a tennis and padel coaching platform.

You are speaking with Coach Toni Alcala from Roger Lederer Academy, Madrid.

{KNOWLEDGE_BASE}

Your role as Orbis Core for coaches:
- Provide data-driven coaching recommendations grounded in Fernando's real Whoop data
- Reference ITF and FIP frameworks specifically when giving technical advice
- Use ATP benchmark comparisons to contextualize performance
- Flag recovery/HRV concerns before recommending training intensity
- Help plan sessions, analyze match patterns, track student progress
- Be concise, professional, and specific — cite actual numbers

Always respond in the same language the coach writes in (English or Spanish).
CRITICAL FORMATTING RULES for Telegram:
- Never use markdown tables, never use ## headers
- Use short paragraphs and bullet points with • only
- Use emojis sparingly for key points
- Keep responses under 200 words
- Be direct and specific with numbers
When referencing Fernando data, use the real numbers from the knowledge base."""

STUDENT_SYSTEM = f"""You are Orbis Core, the AI coaching intelligence for Orbis AI — a tennis and padel coaching platform.

You are speaking with Fernando de los Rios, student at Roger Lederer Academy, Madrid.

{KNOWLEDGE_BASE}

Your role as Orbis Core for students:
- Help Fernando understand his Whoop recovery and HRV data
- Give drill suggestions based on his specific skill gaps (backhand, tactical)
- Support mental preparation using APSQ framework insights
- Celebrate his strengths (forehand 4.2/5, 69% win rate)
- Flag recovery concerns using his real data thresholds
- Connect his wearable data to his actual match performance

Always respond in the same language Fernando writes in (English or Spanish).
CRITICAL FORMATTING RULES for Telegram:
- Never use markdown tables, never use ## headers  
- Use short paragraphs and bullet points with • only
- Use emojis sparingly for key points
- Keep responses under 150 words
- Be encouraging and direct
Reference his real data naturally in conversation.

IMPORTANT RULES:
- Never invent links, surveys or URLs that do not exist
- If Fernando wants to fill a post-session survey or evaluation, tell him to go to:
  https://ai-tennis-academy-platform-mvp.vercel.app/evaluation
- If Fernando asks about his progress report, tell him to go to:
  https://ai-tennis-academy-platform-mvp.vercel.app/report/demo
- Never fabricate data or links not in the knowledge base"""

user_sessions = {}

def get_user_role(user_id):
    return user_sessions.get(user_id, {}).get("role", "student")

def get_conversation_history(user_id):
    return user_sessions.get(user_id, {}).get("history", [])

def add_to_history(user_id, role, content):
    if user_id not in user_sessions:
        user_sessions[user_id] = {"role": "student", "name": "", "history": []}
    history = user_sessions[user_id]["history"]
    history.append({"role": role, "content": content})
    if len(history) > 20:
        history = history[-20:]
    user_sessions[user_id]["history"] = history

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "there"
    if user_id not in user_sessions:
        user_sessions[user_id] = {"role": "student", "name": user_name, "history": []}

    welcome = f"""👋 Hi {user_name}! I'm *Orbis Core*, your AI coaching assistant for Roger Lederer Academy.

I'm ready — just tell me who you are:

👨‍🏫 /coach — I'm Coach Toni
🎾 /student — I'm Fernando"""

    await update.message.reply_text(welcome, parse_mode="Markdown")

async def set_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Coach"
    if user_id not in user_sessions:
        user_sessions[user_id] = {"role": "coach", "name": user_name, "history": []}
    else:
        user_sessions[user_id]["role"] = "coach"
    await update.message.reply_text(f"✅ Switched to *Coach Toni mode*. I have access to Fernando's full Whoop data, APSQ scores, and match analytics. What do you need?", parse_mode="Markdown")

async def set_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Fernando"
    if user_id not in user_sessions:
        user_sessions[user_id] = {"role": "student", "name": user_name, "history": []}
    else:
        user_sessions[user_id]["role"] = "student"
    await update.message.reply_text(f"✅ Switched to *Student mode*. Hi Fernando! I can see your recovery is at 84% today — green light for a hard session. What do you want to work on?", parse_mode="Markdown")

async def fernando_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = """📊 *Fernando — Current Status*

*Whoop Recovery Today:*
🟢 Recovery: 84% — GREEN zone
💓 HRV: 57ms (baseline 55ms — above baseline ✅)
😴 Sleep: 7.4h
❤️ Resting HR: 52 bpm
💪 Strain: 14.2 (yesterday)

*7-Day Averages:*
- Recovery: 76% | HRV: 54ms
- Trend: STABLE-IMPROVING ↗️

*Latest Evaluation (Jun 15, Coach Toni):*
- Forehand: 4.2/5 ✅ Strength
- Backhand: 3.5/5 ⚠️ Main gap
- Serve: 3.8/5
- Movement: 4.0/5
- Tactical: 3.2/5 ⚠️ Priority area

*Match Stats:*
- Win rate: 69% (vs 50% recreational benchmark ✅)
- First serve: 58% (target 60%)
- Unforced errors: 22/match (target <18)

*Next Session:* Thursday Jun 26, 10am
Focus: Backhand slice + serve consistency"""

    await update.message.reply_text(status, parse_mode="Markdown")

async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)

    if role == "coach":
        prompt = """Give me a morning coaching briefing for Fernando based on his real data.
Include: his current recovery status and what intensity is appropriate today, 
the main technical focus area from his last evaluation, 
one specific drill recommendation with ITF framework reference,
and a quick note on his psychological readiness from the APSQ data.
Keep it under 200 words, practical and specific."""
    else:
        prompt = """Give me a morning briefing as Fernando the player.
Include: what my Whoop data means for today's training intensity,
my main focus area to improve based on my last evaluation,
one motivational insight connecting my recovery data to my 69% win rate,
and a tip for Thursday's session with Coach Toni.
Keep it energetic and under 150 words."""

    await update.message.reply_text("⏳ Generating your morning briefing...")

    try:
        system = COACH_SYSTEM if role == "coach" else STUDENT_SYSTEM
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.content[0].text
        add_to_history(user_id, "user", prompt)
        add_to_history(user_id, "assistant", reply)
        await update.message.reply_text(f"🌅 *Morning Briefing*\n\n{reply}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Briefing error: {e}")
        await update.message.reply_text("⚠️ Could not generate briefing. Please try again.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """*Orbis Core — Commands*

/start — Welcome message
/coach — Switch to Coach Toni mode
/student — Switch to Fernando (student) mode
/briefing — Morning briefing with real data
/fernando — Fernando's current Whoop + eval status
/help — This help message

*As Coach Toni, try asking:*
- "Should Fernando train hard today?"
- "What ITF drill should I use for his backhand?"
- "How does Fernando's win rate compare to benchmarks?"
- "Plan Thursday's session based on his recovery"
- "What does his APSQ score mean?"

*As Fernando, try asking:*
- "Is my HRV good today?"
- "What should I focus on to improve my backhand?"
- "How do I prepare mentally before a match?"
- "What padel tactics should I learn?"
- "Why do I win more when my recovery is high?"

*Powered by:*
🔬 Real Whoop data · ITF frameworks · FIP padel guidelines · ATP benchmarks (9,500+ matches)"""

    await update.message.reply_text(help_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    role = get_user_role(user_id)

    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "role": "student",
            "name": update.effective_user.first_name or "",
            "history": []
        }

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        history = get_conversation_history(user_id)
        messages = history + [{"role": "user", "content": user_message}]
        system = COACH_SYSTEM if role == "coach" else STUDENT_SYSTEM

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=system,
            messages=messages
        )

        reply = response.content[0].text
        add_to_history(user_id, "user", user_message)
        add_to_history(user_id, "assistant", reply)

        role_emoji = "🎓" if role == "coach" else "🎾"
        await update.message.reply_text(f"{role_emoji} {reply}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Message error: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("coach", set_coach))
    app.add_handler(CommandHandler("student", set_student))
    app.add_handler(CommandHandler("briefing", briefing))
    app.add_handler(CommandHandler("fernando", fernando_status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Orbis Core bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
