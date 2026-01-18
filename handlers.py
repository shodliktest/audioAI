import os
import tempfile
import asyncio
import re
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile

# Loyihangiz modullari
from config import ADMIN_ID, VOICES
from database import add_user, update_stats, get_stats, get_all_users
from keyboards import main_menu, admin_menu, lang_inline_kb, voices_inline_kb
from utils import read_pdf, read_docx, read_txt, translate_text, generate_audio

router = Router()

class BotStates(StatesGroup):
    waiting_for_broadcast = State()

# --- YORDAMCHI FUNKSIYALAR ---

def get_p_bar(percent):
    """Progress bar vizualizatsiyasi: [▓▓▓░░░░░░░] 30%"""
    filled = int(percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"<code>{bar}</code> {percent}%"

def detect_language_by_chars(text):
    """
    Matn tashqarisidagi tillarni harflar (Unicode) orqali aniqlaydi.
    """
    # Arab harflari (U+0600 - U+06FF)
    if re.search(r'[\u0600-\u06FF]', text):
        return 'ar'
    # Kirill harflari (Rus tili uchun)
    elif re.search(r'[а-яА-ЯёЁ]', text):
        return 'ru'
    # Lotin harflari (Ingliz tili uchun)
    elif re.search(r'[a-zA-Z]', text):
        return 'en'
    return 'en' # Default

def split_text_by_pattern(text):
    """
    Matnni qavs ichi (Uzbek) va tashqarisi (Foreign) ga ajratadi.
    """
    # Qavs ichidagi va tashqarisidagi qismlarni topish (regex)
    pattern = r'(\([^()]+\)|[^()]+)'
    parts = re.findall(pattern, text)
    
    segments = []
    for part in parts:
        clean_part = part.strip()
        if not clean_part:
            continue
            
        if clean_part.startswith("(") and clean_part.endswith(")"):
            # Qavs ichi - HAR DOIM O'ZBEKCHA
            segments.append({
                'text': clean_part[1:-1].strip(), 
                'lang': 'uz'
            })
        else:
            # Qavs tashqarisi - Harflarga qarab aniqlash
            lang = detect_language_by_chars(clean_part)
            segments.append({
                'text': clean_part, 
                'lang': lang
            })
            
    return segments

# --- START VA ADMIN HANDLERLARI ---

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = message.from_user
    add_user(user.id, user.username, user.full_name)
    welcome_text = (f"Assalomu alaykum, <b>{user.full_name}</b>!\n"
                    "Matn yuboring, men uni qavslar asosida aqlli audio qilib beraman.\n\n"
                    "💡 <b>Qoida:</b> Qavs ichidagilar o'zbekcha, tashqaridagilar esa o'z tilida o'qiladi.")
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu(user.id))

@router.message(F.text == "🔐 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin boshqaruv paneli:", reply_markup=admin_menu())

@router.message(F.text == "📊 Statistika")
async def stats_view(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        t, d, u = get_stats()
        await message.answer(f"👥 Foydalanuvchilar: {t}\n📅 Bugun: {d}\n🎙 Audiolar: {u}")

@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_request(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Xabarni kiriting:")
        await state.set_state(BotStates.waiting_for_broadcast)

@router.message(BotStates.waiting_for_broadcast)
async def perform_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    users = get_all_users()
    count = 0
    status_msg = await message.answer(f"⏳ Yuborilmoqda: 0/{len(users)}")
    for u_id in users:
        try:
            await bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
            count += 1
            if count % 10 == 0: await status_msg.edit_text(f"⏳ Yuborilmoqda: {count}/{len(users)}")
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Tugadi. {count} ta foydalanuvchiga yetkazildi.")
    await state.clear()

# --- MATNNI QABUL QILISH ---

@router.message(F.content_type.in_({'text', 'document'}))
async def content_handler(message: types.Message, state: FSMContext, bot: Bot):
    if message.text in ["🔐 Admin Panel", "📊 Statistika", "📢 Xabar yuborish", "🔙 Bosh menyu"]: return
    
    msg = await message.answer(f"⏳ Matn/Fayl tahlil qilinmoqda...\n{get_p_bar(20)}", parse_mode="HTML")
    text = ""
    
    if message.document:
        file = await bot.get_file(message.document.file_id)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            await bot.download_file(file.file_path, tmp.name)
            ext = message.document.file_name.split('.')[-1].lower()
            if ext == 'pdf': text = read_pdf(tmp.name)
            elif ext == 'docx': text = read_docx(tmp.name)
            elif ext == 'txt': text = read_txt(tmp.name)
            os.remove(tmp.name)
    else:
        text = message.text

    if not text:
        await msg.edit_text("❌ Matn topilmadi.")
        return

    await msg.edit_text(f"✅ Tayyor!\n{get_p_bar(100)}\n🌍 Tilni yoki <b>Mix Rejimni</b> tanlang:", parse_mode="HTML", reply_markup=lang_inline_kb())
    await state.update_data(text=text)

# --- AUDIO GENERATSIYA (Mix-Pattern Algoritmi) ---

@router.callback_query(F.data.startswith("lang_"))
async def lang_choice(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text("🗣 Ovoz turini tanlang:", reply_markup=voices_inline_kb(lang))

@router.callback_query(F.data.startswith("voice_"))
async def voice_choice(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    parts = call.data.split("_", 2)
    lang_code, voice_key = parts[1], parts[2]
    
    data = await state.get_data()
    original_text = data.get("text", "")
    output_final = f"audio_{call.from_user.id}.mp3"
    
    try:
        if lang_code == "multi":
            # --- AQLLI MIX ALGORITMI (Qoidalar asosida) ---
            segments = split_text_by_pattern(original_text)
            temp_files = []
            
            await call.message.edit_text(f"🌐 Ko'p tilli tahlil boshlandi...\n{get_p_bar(10)}", parse_mode="HTML")
            
            for i, seg in enumerate(segments):
                tmp_name = f"chunk_{i}_{call.from_user.id}.mp3"
                
                # Ovozni aniqlash
                # seg['lang']: 'uz', 'en', 'ar', 'ru'
                target_lang = seg['lang'] if seg['lang'] in VOICES else 'uz'
                
                # Agar arab tili tanlansa va configda bo'lmasa, 'en' ga fallback qilmasligi uchun
                # VOICES[target_lang] mavjudligini tekshiramiz
                v_id = VOICES[target_lang]['voices'][voice_key]['id']
                
                await generate_audio(seg['text'], v_id, tmp_name)
                temp_files.append(tmp_name)
                
                prog = 10 + int((i+1)/len(segments) * 80)
                await call.message.edit_text(f"🎙 Audio bo'laklar yozilmoqda ({i+1}/{len(segments)})...\n{get_p_bar(prog)}", parse_mode="HTML")

            # Binary ulanish
            with open(output_final, "wb") as outfile:
                for f in temp_files:
                    with open(f, "rb") as infile:
                        outfile.write(infile.read())
                    os.remove(f)
            rejim_label = "Ko'p tilli (Pattern Mix)"
            
        else:
            # --- STANDART TARJIMA ---
            await call.message.edit_text(f"🌍 Tarjima qilinmoqda...\n{get_p_bar(40)}", parse_mode="HTML")
            final_text = await translate_text(original_text, lang_code)
            v_id = VOICES[lang_code]['voices'][voice_key]['id']
            await generate_audio(final_text, v_id, output_final)
            rejim_label = f"Tarjima ({lang_code})"

        await call.message.edit_text(f"📤 Telegramga yuklanmoqda...\n{get_p_bar(95)}", parse_mode="HTML")
        await bot.send_audio(call.message.chat.id, FSInputFile(output_final), caption=f"✅ {rejim_label} tayyor!")
        update_stats()
        
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        if os.path.exists(output_final): os.remove(output_final)
        await call.message.delete()
        await state.clear()

@router.callback_query(F.data == "back_to_lang")
async def back_to_lang(call: types.CallbackQuery):
    await call.message.edit_text("🌍 Tilni yoki rejimni tanlang:", reply_markup=lang_inline_kb())
