import asyncio
import streamlit as st
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from groq import Groq
import threading

# 1. Streamlit Secrets'dan ma'lumotlarni olish
# Dashboard -> Settings -> Secrets qismida BOT_TOKEN va GROQ_API_KEY bo'lishi shart
BOT_TOKEN = st.secrets["BOT_TOKEN"]
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# 2. Bot va AI obyektlarini yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

# --- BOT LOGIKASI ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"Salom {message.from_user.first_name}! 🇬🇧\nMen AI repetitorman. Gaplaringizni tekshirishga tayyorman.")

@dp.message(F.text)
async def handle_ai(message: types.Message):
    prompt = f"Correct this English sentence and explain in Uzbek: '{message.text}'"
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
        )
        await message.answer(completion.choices[0].message.content)
    except Exception as e:
        await message.answer("Xatolik yuz berdi. Keyinroq urinib ko'ring.")

# --- STREAMLIT BILAN BOG'LASH ---

async def start_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def run_bot_in_thread():
    """Botni alohida oqimda ishga tushirish funksiyasi"""
    if "bot_started" not in st.session_state:
        loop = asyncio.new_event_loop()
        def target():
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_bot())
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        st.session_state.bot_started = True
    
