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

# 1. Botni ishga tushirishning asosiy funksiyasi
async def start_bot():
    # Ma'lumotlar bazasini tekshirish/yaratish
    init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Routerni (handlers) ulash
    dp.include_router(router)
    
    # Eskirgan xabarlarni o'chirib yuborish
    await bot.delete_webhook(drop_pending_updates=True)
    
    # MUHIM: Streamlit Cloud-da RuntimeError bermasligi uchun handle_signals=False
    await dp.start_polling(bot, handle_signals=False)

# 2. Botni alohida Thread (oqim) ichida yurgizish funksiyasi
def run_bot_thread():
    # Yangi oqim uchun yangi asyncio event loop yaratamiz
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

# 3. Streamlit Web Interfeysi
if __name__ == "__main__":
    # Loglarni sozlash
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    st.set_page_config(page_title="AudioAI Dashboard", page_icon="🎙")
    st.title("🎙 Telegram TTS & AudioAI")
    
    st.markdown("""
    ### Bot Holati: `Faol ✅`
    Ushbu sahifa botingizni Streamlit Cloud serverida 'uyg'oq' saqlash va 
    kelajakda statistikani vizual ko'rish uchun xizmat qiladi.
    """)

    # Bot faqat bir marta ishga tushishini ta'minlash (Session State orqali)
    if 'bot_running' not in st.session_state:
        # Alohida thread yaratish va daemon=True qilish (Streamlit yopilsa u ham yopilishi uchun)
        thread = threading.Thread(target=run_bot_thread, daemon=True)
        thread.start()
        st.session_state['bot_running'] = True
        st.success("Telegram Bot fon rejimida muvaffaqiyatli ishga tushdi!")

    # Admin uchun qisqa statistika vidjeti
    if st.button("Serverni yangilash"):
        st.experimental_rerun()
