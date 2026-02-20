import asyncio
import logging
import sys
import threading
import streamlit as st
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Loyihangizdagi boshqa fayllardan import qilish
from config import BOT_TOKEN
from database import init_db
from handlers import router

# 1. Botni ishga tushirishning asosiy funksiyasi
async def start_bot():
    # Ma'lumotlar bazasini yaratish/tekshirish
    init_db()
    
    # Bot va Dispatcher sozlamalari
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Routerni ulash
    dp.include_router(router)
    
    # Eskirgan xabarlarni o'chirib yuborish (Webhookni tozalash)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # DIQQAT: handle_signals=False Streamlit Cloud-dagi RuntimeError-ni oldini oladi
    await dp.start_polling(bot, handle_signals=False)

# 2. Botni alohida oqimda (Thread) yurgizish funksiyasi
def run_bot_in_thread():
    # Yangi thread uchun yangi asyncio event loop yaratamiz
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

# 3. Streamlit Web Interfeysi
if __name__ == "__main__":
    # Loglarni sozlash (Xatolarni terminalda ko'rish uchun)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    st.set_page_config(page_title="AudioAI Control", page_icon="🎙")
    st.title("🎙 Telegram TTS Bot Dashboard")
    
    st.markdown("""
    ### Bot Holati: `Faol ✅`
    Ushbu dashboard botingizni serverda (Streamlit Cloud) o'chib qolmasdan ishlashini ta'minlaydi.
    """)

    # Bot faqat bir marta ishga tushishini ta'minlash (st.session_state orqali)
    if 'bot_thread_started' not in st.session_state:
        # Alohida thread yaratish
        thread = threading.Thread(target=run_bot_in_thread, daemon=True)
        thread.start()
        st.session_state['bot_thread_started'] = True
        st.success("Telegram Bot fon rejimida muvaffaqiyatli ishga tushdi!")

    # Statistika vidjeti uchun joy (ixtiyoriy)
    st.divider()
    if st.button("🔄 Serverni yangilash"):
        st.rerun() # Oldingi experimental_rerun o'rniga yangi rerun ishlatildi
