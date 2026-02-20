import os
import asyncio
import re
import html  # HTML teglari bilan bog'liq xatolarni oldini olish uchun
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile

from config import ADMIN_ID, VOICES
from database import add_user, update_stats, get_stats, get_all_users
from keyboards import main_menu, admin_menu, lang_inline_kb, voices_inline_kb
from utils import read_pdf, read_docx, read_txt, translate_text, generate_audio

router = Router()

class BotStates(StatesGroup):
    waiting_for_broadcast = State()

# --- Yordamchi Funksiyalar ---

def get_p_bar(percent):
    """Jarayon satrini (progress bar) yaratish"""
    filled = int(percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"<code>{bar}</code> {percent}%"

def split_message(text, max_length=4000):
    """Uzun matnni Telegram limiti (4096) bo'yicha bo'laklarga bo'lish"""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# --- Asosiy Handlerlar ---

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Noma'lum"
    fullname = message.from_user.full_name
    
    add_user(user_id, username, fullname)
    
    welcome_text = (
        f"👋 <b>Assalomu alaykum, {fullname}!</b>\n\n"
        "Men matnlarni professional darajada tarjima qiluvchi va "
        "ulardan audio (TTS) yaratuvchi aqlli botman.\n\n"
        "👇 <b>Boshlash uchun matn yuboring yoki fayl yuklang:</b>"
    )
    await message.answer(welcome_text, reply_markup=main_menu(user_id), parse_mode="HTML")

# --- Matn va Fayllarni Qabul Qilish ---

@router.message(F.text | F.document)
async def handle_input(message: types.Message, state: FSMContext):
    # Admin menyusi tugmalari bosilganda ishlamasligi uchun
    if message.text in ["📊 Statistika", "📢 Xabar yuborish", "🔐 Admin Panel", "🔙 Bosh menyu", "ℹ️ Yordam"]:
        if message.text == "ℹ️ Yordam":
            await unknown_message_handler(message)
        return

    text = ""
    # Matn bo'lsa
    if message.text:
        text = message.text
    # Fayl bo'lsa
    elif message.document:
        file_id = message.document.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        
        ext = message.document.file_name.split('.')[-1].lower()
        tmp_path = f"temp_{file_id}.{ext}"
        
        await message.bot.download_file(file_path, tmp_path)
        
        if ext == 'pdf': text = read_pdf(tmp_path)
        elif ext == 'docx': text = read_docx(tmp_path)
        elif ext == 'txt': text = read_txt(tmp_path)
        
        if os.path.exists(tmp_path): os.remove(tmp_path)

    if not text or len(text.strip()) < 2:
        await message.answer("⚠️ Iltimos, tahlil qilish uchun mazmunli matn yuboring.")
        return

    # Matnni saqlash va til tanlashni ko'rsatish
    await state.update_data(original_text=text)
    await message.answer(
        f"✅ Matn qabul qilindi ({len(text)} belgi).\n\n"
        "🌍 <b>Qaysi tilga tarjima qilish va o'qish kerak?</b>", 
        reply_markup=lang_inline_kb(), 
        parse_mode="HTML"
    )

# --- Tarjima va Ovoz Berish Jarayoni ---

@@router.callback_query(F.data.startswith("voice_"))
async def process_voice(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    # data ni to'g'ri ajratib olish (voice_uz_female_1 -> ["voice", "uz", "female", "1"])
    data = call.data.split("_")
    lang_code = data[1]
    
    # voice_key ni qayta tiklash (female + _ + 1)
    voice_key = f"{data[2]}_{data[3]}" 
    
    user_data = await state.get_data()
    # ... qolgan kod o'zgarishsiz qoladi

    original_text = user_data.get("original_text")
    output_final = f"result_{call.from_user.id}.mp3"
    
    try:
        await call.message.edit_text(f"⏳ <b>Akademik tarjima qilinmoqda...</b>\n{get_p_bar(40)}", parse_mode="HTML")
        
        # 1. Akademik darajadagi to'liq tarjima (utils.py dagi yangi mantiq)
        final_text = await translate_text(original_text, lang_code)
        
        # 2. Audio fayl yaratish
        await call.message.edit_text(f"🎙 <b>Audio o'qilmoqda...</b>\n{get_p_bar(70)}", parse_mode="HTML")
        v_id = VOICES[lang_code]['voices'][voice_key]['id']
        await generate_audio(final_text, v_id, output_final)
        
        # 3. Natijani yuborish
        await call.message.edit_text(f"📤 <b>Yuklanmoqda...</b>\n{get_p_bar(95)}", parse_mode="HTML")
        
        voice_name = VOICES[lang_code]['voices'][voice_key]['name']
        caption = (f"✅ <b>Audio Tayyor!</b>\n"
                   f"🎙 Ovoz: {voice_name}\n"
                   f"🌍 Til: {lang_code.upper()}")
        
        await bot.send_audio(call.message.chat.id, FSInputFile(output_final), caption=caption, parse_mode="HTML")

        # 4. UZUN MATNNI BO'LIB YUBORISH (Xatoliksiz va to'liq)
        # html.escape tarjima ichidagi < > belgilarini zararsizlantiradi
        safe_text = html.escape(final_text)
        chunks = split_message(safe_text)
        
        for i, chunk in enumerate(chunks):
            header = f"📝 <b>Matn ({i+1}-qism):</b>\n\n" if len(chunks) > 1 else "📝 <b>To'liq matn:</b>\n\n"
            await bot.send_message(call.message.chat.id, f"{header}{chunk}", parse_mode="HTML")
            await asyncio.sleep(0.5) # Ketma-ketlik va bloklanishni oldini olish uchun

        update_stats()
        
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {html.escape(str(e))}")
    finally:
        if os.path.exists(output_final): os.remove(output_final)
        await call.message.delete()
        await state.clear()

# --- ⚠️ MUKAMMAL YO'RIQNOMA (Noto'g'ri xabar yozilganda) ---

@router.message()
async def unknown_message_handler(message: types.Message):
    """Foydalanuvchi adashib xabar yozsa yoki yo'riqnoma so'rasa"""
    
    guide_text = (
        "📖 <b>Botdan foydalanish bo'yicha mukammal qo'llanma</b>\n\n"
        "Siz bu bot orqali har qanday matnni professional audyoga aylantirishingiz mumkin. "
        "Bot matnni qisqartirmaydi va akademik darajada tarjima qiladi.\n\n"
        "🚀 <b>Qanday foydalanish kerak?</b>\n\n"
        "1️⃣ <b>Matn yuboring:</b> Shunchaki botga istalgan tildagi matnni yozib yuboring.\n"
        "2️⃣ <b>Fayl yuboring:</b> PDF, DOCX (Word) yoki TXT fayllarni botga tashlang. Bot ularni o'zi o'qib oladi.\n"
        "3️⃣ <b>Tilni tanlang:</b> Matn yuborganingizdan so'ng, pastda tillar chiqadi. Tarjima qilmoqchi bo'lgan tilingizni bosing.\n"
        "4️⃣ <b>Ovozni tanlang:</b> Erkak yoki ayol ovozidan birini tanlang.\n\n"
        "✨ <b>Natija:</b> Bot sizga tarjima qilingan matnni bir nechta xabar bo'lsa ham to'liq yuboradi va uni professional ovozda o'qib beradi.\n\n"
        "<i>Hozirning o'zida biror matn yuborib ko'ring!</i>"
    )
    
    await message.answer(guide_text, parse_mode="HTML", reply_markup=main_menu(message.from_user.id))

# (Admin panel callbacklari o'zgarishsiz qoladi...)
@router.callback_query(F.data == "lang_multi")
async def lang_multi_choice(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("🌐 Smart Mix rejimida ovoz turini tanlang:", reply_markup=voices_inline_kb("multi"))

@router.callback_query(F.data.startswith("lang_"))
async def lang_choice(call: types.CallbackQuery):
    lang_code = call.data.split("_")[1]
    await call.message.edit_text(f"🎙 {VOICES[lang_code]['label']} tili uchun ovozni tanlang:", reply_markup=voices_inline_kb(lang_code))
    

