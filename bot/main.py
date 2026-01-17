import asyncio
import streamlit as st
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# Streamlit Secrets'dan ma'lumotlarni olish
# Bularni Streamlit Dashboard -> Settings -> Secrets qismiga yozgan bo'lishingiz shart
BOT_TOKEN = st.secrets["BOT_TOKEN"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Salom {message.from_user.first_name}! 👋\n"
        "Men Streamlit orqali ishlaydigan AI repetitorman. "
        "Kalitlar muvaffaqiyatli ulandi! ✅"
    )

async def start_polling():
    # Botni ishga tushirish
    await dp.start_polling(bot)

def run_bot_logic():
    # Yangi event loop yaratish (Streamlit uchun majburiy)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_polling())
