import asyncio
import logging
import json
import sqlite3
import threading
import streamlit as st
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

# --- 1. SOZLAMALAR VA LOGGING ---
logging.basicConfig(level=logging.INFO)

# Streamlit Secrets
try:
    BOT_TOKEN = st.secrets["BOT_TOKEN"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("Secrets topilmadi! .streamlit/secrets.toml ni tekshiring.")
    st.stop()

# --- 2. DATABASE (SQLite) ---
# Oddiy va ishonchli. Keyinchalik Firebasega o'tkazish oson.
DB_NAME = "english_tutor.db"

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    # Foydalanuvchi profili
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            level TEXT DEFAULT 'A1',
            xp INTEGER DEFAULT 0
        )
    ''')
    # Testlar tarixi (takrorlanmaslik uchun)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            question_hash TEXT,
            is_correct BOOLEAN
        )
    ''')
    conn.commit()
    return conn

db_conn = init_db()

def get_user(user_id):
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def register_user(user_id, full_name):
    cursor = db_conn.cursor()
    if not get_user(user_id):
        cursor.execute("INSERT INTO users (user_id, full_name) VALUES (?, ?)", (user_id, full_name))
        db_conn.commit()

def update_xp(user_id, points):
    cursor = db_conn.cursor()
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (points, user_id))
    db_conn.commit()

# --- 3. AI ENGINE (GROQ) ---
client = Groq(api_key=GROQ_API_KEY)

async def get_ai_explanation(topic, level):
    """Mavzuni tushuntirib beradi"""
    prompt = f"""
    You are an expert English teacher. Explain the topic '{topic}' to a student with level '{level}'.
    Structure:
    1. What is it? (Simple definition in Uzbek)
    2. Formula (Positive, Negative, Question)
    3. One real-life example with translation.
    Keep it concise and friendly. Use emojis.
    Response must be in Uzbek.
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192", # Kuchliroq model
        )
        return response.choices[0].message.content
    except Exception as e:
        return "⚠️ AI bilan bog'lanishda xatolik."

async def generate_quiz_question(topic, level):
    """JSON formatda test tuzadi"""
    prompt = f"""
    Create a multiple-choice question for English topic '{topic}' suitable for level '{level}'.
    Return ONLY valid JSON format:
    {{
        "question": "The English sentence with a blank or context",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_option_index": 0,
        "explanation": "Why this is correct (in Uzbek)"
    }}
    Do not add any text outside JSON.
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "system", "content": "You are a JSON generator."}, 
                      {"role": "user", "content": prompt}],
            model="llama3-70b-8192",
            temperature=0.7 # Kreativlik uchun
        )
        content = response.choices[0].message.content
        # JSONni tozalash (ba'zan ```json deb qaytaradi)
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        return json.loads(content)
    except Exception as e:
        logging.error(f"JSON Error: {e}")
        return None

# --- 4. BOT STATES & LOGIC ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class TutorStates(StatesGroup):
    choosing_topic = State()
    learning = State()
    quiz = State()

# Klaviaturalar
def main_menu_kb():
    kb = [
        [InlineKeyboardButton(text="📘 Present Simple", callback_data="topic:Present Simple")],
        [InlineKeyboardButton(text="📊 Mening Profilim", callback_data="profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def quiz_control_kb():
    kb = [
        [InlineKeyboardButton(text="🧪 Test ishlash", callback_data="start_quiz")],
        [InlineKeyboardButton(text="🔙 Menyuga qaytish", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def options_kb(options):
    kb = []
    for i, opt in enumerate(options):
        kb.append([InlineKeyboardButton(text=opt, callback_data=f"ans:{i}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    register_user(message.from_user.id, message.from_user.full_name)
    await message.answer(
        f"Salom, {message.from_user.first_name}! 👋\n"
        "Men sizning shaxsiy AI ingliz tili ustozingizman.\n"
        "Qaysi mavzudan boshlaymiz?",
        reply_markup=main_menu_kb()
    )

@dp.callback_query(F.data == "menu")
async def back_to_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Asosiy menyu:", reply_markup=main_menu_kb())

# 1. Mavzu tanlash va tushuntirish
@dp.callback_query(F.data.startswith("topic:"))
async def topic_selected(call: types.CallbackQuery, state: FSMContext):
    topic = call.data.split(":")[1]
    user = get_user(call.from_user.id)
    level = user[2] # Level column
    
    await call.message.edit_text(f"⏳ **{topic}** mavzusi ({level}) tayyorlanmoqda...")
    
    explanation = await get_ai_explanation(topic, level)
    
    # State ga mavzuni saqlaymiz
    await state.update_data(current_topic=topic, level=level)
    await state.set_state(TutorStates.learning)
    
    await call.message.edit_text(
        explanation, 
        reply_markup=quiz_control_kb(), 
        parse_mode="Markdown"
    )

# 2. Test generatsiya qilish
@dp.callback_query(F.data == "start_quiz")
async def start_quiz(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    topic = data.get("current_topic")
    level = data.get("level")
    
    await call.message.edit_text("🧠 AI savol tuzmoqda...")
    
    quiz_data = await generate_quiz_question(topic, level)
    
    if not quiz_data:
        await call.message.edit_text("Xatolik bo'ldi. Qayta urinib ko'ring.", reply_markup=quiz_control_kb())
        return

    # Javobni saqlab qolamiz
    await state.update_data(correct_index=quiz_data['correct_option_index'], explanation=quiz_data['explanation'])
    await state.set_state(TutorStates.quiz)
    
    await call.message.edit_text(
        f"📝 **Test: {topic}**\n\n{quiz_data['question']}",
        reply_markup=options_kb(quiz_data['options'])
    )

# 3. Javobni tekshirish
@dp.callback_query(F.data.startswith("ans:"), TutorStates.quiz)
async def check_answer(call: types.CallbackQuery, state: FSMContext):
    user_idx = int(call.data.split(":")[1])
    data = await state.get_data()
    correct_idx = data.get("correct_index")
    explanation = data.get("explanation")
    
    if user_idx == correct_idx:
        # To'g'ri javob
        update_xp(call.from_user.id, 10)
        msg = f"✅ **To'g'ri!** (+10 XP)\n\n{explanation}"
    else:
        # Xato javob
        msg = f"❌ **Xato.**\n\n{explanation}"
    
    # Keyingi qadam tugmalari
    kb = [
        [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data="start_quiz")],
        [InlineKeyboardButton(text="🛑 Yetarli", callback_data="menu")]
    ]
    
    await call.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

# --- SERVERNI ISHGA TUSHIRISH ---

async def main_bot_logic():
    await bot.delete_webhook(drop_pending_updates=True)
    # handle_signals=False Streamlit thread xatosini oldini oladi
    await dp.start_polling(bot, handle_signals=False)

def run_bot_thread():
    if "bot_active" not in st.session_state:
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=lambda: (asyncio.set_event_loop(loop), loop.run_until_complete(main_bot_logic())), daemon=True)
        t.start()
        st.session_state.bot_active = True

# UI qismi
st.title("🎓 AI English Tutor Dashboard")
st.write("Bot statusi: Active 🟢")
run_bot_thread()

if st.button("Bazani ko'rish"):
    conn = init_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    st.write(users)
