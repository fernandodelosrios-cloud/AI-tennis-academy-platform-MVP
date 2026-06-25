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

COACH_SYSTEM = """You are Orbis Core, an AI coaching assistant for tennis and padel coaches.
You help coaches with:
- Daily player briefings based on recovery and HRV data
- Session planning and drill recommendations
- Match analysis and tactical advice
- Student progress tracking
- ITF and FIP coaching framework guidance

You have access to knowledge from:
- ITF Coaching Frameworks (Level 1-3)
- FIP Padel coaching guidelines
- Sports science research on HRV and load management
- ATP match benchmarks (9,500+ matches)

Be concise, practical, and data-driven. Always reference relevant frameworks when giving advice.
Respond in the same language the coach writes in (English or Spanish).
Format responses clearly with short paragraphs. Use emojis sparingly for key points."""

STUDENT_SYSTEM = """You are Orbis Core, an AI coaching assistant for tennis and padel students/players.
You help students with:
- Understanding their recovery and HRV data
- Pre-match mental preparation (APSQ framework)
- Drill suggestions to improve specific skills
- Match preparation and tactical tips
- Nutrition and recovery advice

You have access to knowledge from:
- ITF player development frameworks
- Sports science research on HRV and recovery
- Mental performance (APSQ) guidelines
- Nutrition guidance for tennis athletes

Be encouraging, clear, and actionable. Keep advice practical and easy to implement.
Respond in the same language the student writes in (English or Spanish).
Use a supportive tone — you are their personal AI coaching companion."""

user_sessions = {}

def get_user_role(user_id: int) -> str:
    return user_sessions.get(user_id, {}).get("role", "student")

def get_user_name(user_id: int) -> str:
    return user_sessions.get(user_id, {}).get("name", "")

def get_conversation_history(user_id: int) -> list:
    return user_sessions.get(user_id, {}).get("history", [])

def add_to_history(user_id: int, role: str, content: str):
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
    
    welcome = f"""👋 Hi {user_name}! I'm *Orbis Core*, your AI coaching assistant.

I can help you with:
🎾 Training plans and drill recommendations
📊 Recovery and HRV analysis
🧠 Mental performance and pre-match prep
📋 ITF/FIP coaching frameworks
🏆 Match analysis and tactics

*Commands:*
/coach — Switch to coach mode
/student — Switch to student mode
/briefing — Get your morning briefing
/help — Show all commands

Just send me a message to get started!"""
    
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def set_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Coach"
    if user_id not in user_sessions:
        user_sessions[user_id] = {"role": "coach", "name": user_name, "history": []}
    else:
        user_sessions[user_id]["role"] = "coach"
        user_sessions[user_id]["name"] = user_name
    await update.message.reply_text(f"✅ Switched to *Coach mode*, {user_name}. Ask me anything about your students, training plans, or coaching frameworks.", parse_mode="Markdown")

async def set_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Player"
    if user_id not in user_sessions:
        user_sessions[user_id] = {"role": "student", "name": user_name, "history": []}
    else:
        user_sessions[user_id]["role"] = "student"
        user_sessions[user_id]["name"] = user_name
    await update.message.reply_text(f"✅ Switched to *Student mode*, {user_name}. Ask me about your training, recovery, or match prep!", parse_mode="Markdown")

async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    name = get_user_name(user_id) or update.effective_user.first_name or ""
    
    if role == "coach":
        prompt = f"Give me a concise morning coaching briefing for today. Include: key focus areas for training sessions, recovery considerations, and one tactical tip from ITF frameworks. Keep it practical and under 200 words."
    else:
        prompt = f"Give me a motivating morning briefing for a tennis player. Include: mindset tip for today, a quick physical activation suggestion, and one technical focus for training. Keep it energetic and under 150 words."
    
    await update.message.reply_text("⏳ Generating your morning briefing...")
    
    try:
        system = COACH_SYSTEM if role == "coach" else STUDENT_SYSTEM
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
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
/coach — Switch to coach mode
/student — Switch to student mode  
/briefing — Get your morning briefing
/help — Show this help

*As a coach, you can ask:*
- "Plan a backhand drill for intermediate players"
- "What does ITF Level 2 say about serve technique?"
- "My student has 65% recovery today, should we do a light session?"
- "Give me a padel tactical drill for doubles"

*As a student, you can ask:*
- "My HRV is 45ms today, should I train hard?"
- "Help me with my pre-match routine"
- "What drills can I do to improve my forehand?"
- "I'm feeling anxious before my match, what can I do?"

Just type your question and I'll answer!"""
    
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
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
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
        await update.message.reply_text("⚠️ Something went wrong. Please try again in a moment.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("coach", set_coach))
    app.add_handler(CommandHandler("student", set_student))
    app.add_handler(CommandHandler("briefing", briefing))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Orbis Core bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
