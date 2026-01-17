import streamlit as st
import asyncio
import threading
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from bot.config import BOT_TOKEN

# --- STREAMLIT INTERFEYSI ---
st.set_page_config(page_title="AI English Tutor Control Panel", page_icon="🇬🇧")
st.title("🤖 AI English Tutor")
st.write("Bot holati: Ishlamoqda ✅")

# --- BOT LOGIKASI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Salom {message.from_user.full_name}! 👋\n\n"
        "Men Streamlit orqali boshqariladigan AI repetitorman.\n"
        "Tayyor bo'lsangiz, o'qishni boshlaymiz!"
    )

async def start_bot():
    await dp.start_polling(bot)

# Botni alohida oqimda ishga tushirish funksiyasi
def run_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

# Streamlit qayta yuklanganda bot o'chib qolmasligi uchun
if "bot_started" not in st.session_state:
    thread = threading.Thread(target=run_bot_thread, daemon=True)
    thread.start()
    st.session_state.bot_started = True
    st.success("Bot muvaffaqiyatli ishga tushirildi!")

st.sidebar.header("Statistika")
st.sidebar.write("Hozircha foydalanuvchilar: 1")
