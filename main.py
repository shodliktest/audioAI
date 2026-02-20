import asyncio
import logging
import sys
import threading
import streamlit as st
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import router # Router import qilingan

async def start_bot():
    init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # DIQQAT: Router faqat start_bot ichida ulanishi kerak
    # Bu har safar yangi dp yaratilganda unga routerni biriktiradi
    if router.parent_router is not None:
        router.parent_router = None # Avvalgi bog'liqlikni uzish (tozalash)

    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, handle_signals=False)

def run_bot_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    st.set_page_config(page_title="AudioAI Control", page_icon="🎙")
    st.title("🎙 Telegram TTS Bot Dashboard")

    # Session state orqali faqat bir marta thread ochish
    if 'bot_thread_started' not in st.session_state:
        thread = threading.Thread(target=run_bot_in_thread, daemon=True)
        thread.start()
        st.session_state['bot_thread_started'] = True
        st.success("Bot muvaffaqiyatli ishga tushdi!")

    st.divider()
    if st.button("🔄 Serverni yangilash"):
        st.rerun()
        
