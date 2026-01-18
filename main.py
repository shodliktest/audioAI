import asyncio
import logging
import sys
import threading
import streamlit as st
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# O'zingiz yaratgan fayllardan import qilish
from config import BOT_TOKEN
from database import init_db
from handlers import router

# 1. Botni ishga tushirish funksiyasi
async def start_bot():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    # handle_signals=False Streamlit Cloud uchun zarur
    await dp.start_polling(bot, handle_signals=False)

# 2. Botni alohida Thread ichida yurgizish
def run_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

# 3. Streamlit Interfeysi
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    st.set_page_config(page_title="AudioAI Dashboard", page_icon="🎙")
    st.title("🎙 Telegram TTS & AudioAI")
    
    if 'bot_running' not in st.session_state:
        thread = threading.Thread(target=run_bot_thread, daemon=True)
        thread.start()
        st.session_state['bot_running'] = True
        st.success("Telegram Bot faollashtirildi! ✅")

    st.info("Bot hozirda Telegramda foydalanuvchilarga xizmat ko'rsatmoqda.")

    # Sahifani yangilash tugmasi
    if st.button("Serverni yangilash"):
        st.rerun() # experimental_rerun o'rniga ishlatiladi
