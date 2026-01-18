import os
import tempfile
import asyncio
from datetime import datetime
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# O'zimizning modullar
from config import ADMIN_ID, VOICES
from database import add_user, update_stats, get_stats, get_all_users
from keyboards import main_menu, admin_menu, lang_inline_kb, voices_inline_kb
from utils import read_pdf, read_docx, read_txt, translate_text, generate_audio

router = Router()

# Bot holatlari
class BotStates(StatesGroup):
    waiting_for_broadcast = State()
    processing_tts = State()

# --- PROGRESS BAR FUNKSIYASI ---
def get_p_bar(percent):
    """Jarayonni vizual ko'rsatish: [▓▓▓░░░░░░░] 30%"""
    filled = int(percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"<code>{bar}</code> {percent}%"

# --- START VA ASOSIY BUYRUQLAR ---
@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = message.from_user
    add_user(user.id, user.username, user.full_name)
    welcome_text = (f"Assalomu alaykum, <b>{user.full_name}</b>!\n"
                    "Matn yuboring yoki fayl (PDF, DOCX, TXT) yuklang.\n"
                    "Men uni tarjima qilib, ovozli xabarga aylantirib beraman.")
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu(user.id))

@router.message(F.text == "ℹ️ Yordam")
async def help_handler(message: types.Message):
    help_text = ("<b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
                 "1. Botga matn yozing yoki fayl yuboring.\n"
                 "2. Tilni va tarjima rejimini tanlang.\n"
                 "3. O'zingizga yoqqan ovozni tanlang.\n"
                 "4. Bot sizga tayyor audio faylni yuboradi.")
    await message.answer(help_text, parse_mode="HTML")

@router.message(F.text == "📞 Bog'lanish")
async def contact_handler(message: types.Message):
    await message.answer("Savollar bo'yicha admin bilan bog'laning: @AdminUsername")

# --- ADMIN PANEL VA BROADCAST LOGIKASI ---
@router.message(F.text == "🔐 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin boshqaruv paneli:", reply_markup=admin_menu())

@router.message(F.text == "📊 Statistika")
async def stats_view(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        t, d, u = get_stats()
        text = (f"📈 <b>Bot statistikasi:</b>\n\n"
                f"👥 Jami foydalanuvchilar: {t}\n"
                f"📅 Bugungi faollik: {d}\n"
                f"🎙 Jami yaratilgan audiolar: {u}")
        await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_request(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni kiriting (Matn, rasm yoki video):")
        await state.set_state(BotStates.waiting_for_broadcast)

@router.message(BotStates.waiting_for_broadcast)
async def perform_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    users = get_all_users()
    count = 0
    status_msg = await message.answer(f"⏳ Xabar yuborish boshlandi: 0/{len(users)}")
    
    for u_id in users:
        try:
            await bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
            count += 1
            if count % 10 == 0:
                await status_msg.edit_text(f"⏳ Yuborilmoqda: {count}/{len(users)}")
            await asyncio.sleep(0.05)
        except: pass
            
    await message.answer(f"✅ Xabar yuborish tugadi.\nJami yetkazildi: {count} ta foydalanuvchiga.")
    await state.clear()

# --- REJIMLARNI BOSHQARISH (MODE SWITCH) ---
@router.callback_query(F.data == "set_mode_original")
async def set_mode_original(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(mode="original")
    await call.message.edit_text(
        "<b>⚠️ Tarjimasiz rejim:</b>\nMatn o'z holaticha o'qiladi. Tilni tanlang:",
        parse_mode="HTML", reply_markup=lang_inline_kb(mode="original")
    )

@router.callback_query(F.data == "set_mode_translate")
async def set_mode_translate(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(mode="translate")
    await call.message.edit_text(
        "<b>🌍 Tarjima rejimi:</b>\nMatn tanlangan tilga tarjima qilinadi:",
        parse_mode="HTML", reply_markup=lang_inline_kb(mode="translate")
    )

# --- MATN VA FAYL QABUL QILISH ---
@router.message(F.content_type.in_({'text', 'document'}))
async def content_handler(message: types.Message, state: FSMContext, bot: Bot):
    # Admin tugmalarini chetlab o'tish
    if message.text in ["🔐 Admin Panel", "📊 Statistika", "📢 Xabar yuborish", "🔙 Bosh menyu"]: return

    msg = await message.answer(f"⏳ Jarayon boshlanmoqda...\n{get_p_bar(10)}", parse_mode="HTML")
    text = ""

    if message.document:
        if message.document.file_size > 20*1024*1024:
            await msg.edit_text("❌ Fayl juda katta (limit 20MB).")
            return

        file = await bot.get_file(message.document.file_id)
        await msg.edit_text(f"⏳ Fayl yuklanmoqda...\n{get_p_bar(30)}", parse_mode="HTML")
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            await bot.download_file(file.file_path, tmp.name)
            await msg.edit_text(f"⏳ Matn qayta ishlanmoqda...\n{get_p_bar(60)}", parse_mode="HTML")
            
            ext = message.document.file_name.split('.')[-1].lower()
            if ext == 'pdf': text = await read_pdf(tmp.name)
            elif ext == 'docx': text = await read_docx(tmp.name)
            elif ext == 'txt': text = await read_txt(tmp.name)
            os.remove(tmp.name)
    else:
        text = message.text
        await msg.edit_text(f"⏳ Matn tahlil qilinmoqda...\n{get_p_bar(70)}", parse_mode="HTML")

    if not text or len(text.strip()) < 2:
        await msg.edit_text("❌ Xatolik: Matn topilmadi yoki juda qisqa.")
        return

    await msg.edit_text(f"✅ Tayyor!\n{get_p_bar(100)}", parse_mode="HTML")
    await asyncio.sleep(0.5)

    await state.update_data(text=text, mode="translate") # Standart: Tarjima
    await msg.edit_text("🌍 Kerakli tilni tanlang:", reply_markup=lang_inline_kb())

# --- TIL VA OVOZ CALLBACKLARI ---
@router.callback_query(F.data.startswith("lang_"))
async def lang_choice(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text("🗣 Ovozni va ovoz turini tanlang:", reply_markup=voices_inline_kb(lang))

@router.callback_query(F.data.startswith("voice_"))
async def voice_choice(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    # split("_", 2) orqali 'female_1' kabi kalitlarni to'g'ri ajratamiz
    parts = call.data.split("_", 2)
    lang_code, voice_key = parts[1], parts[2]
    
    data = await state.get_data()
    mode = data.get("mode", "translate")
    original_text = data.get("text", "")
    voice_info = VOICES[lang_code]['voices'][voice_key]
    
    # 1-bosqich: Tarjima (Progress: 30%)
    await call.message.edit_text(f"⏳ Tayyorlanmoqda...\n{get_p_bar(20)}", parse_mode="HTML")
    
    if mode == "translate":
        await call.message.edit_text(f"🌍 Tarjima qilinmoqda...\n{get_p_bar(40)}", parse_mode="HTML")
        final_text = await translate_text(original_text, lang_code)
    else:
        final_text = original_text
    
    # 2-bosqich: Ovozlashtirish (Progress: 70%)
    await call.message.edit_text(f"🎙 Ovoz berilmoqda: <b>{voice_info['name']}</b>\n{get_p_bar(70)}", parse_mode="HTML")
    output = f"audio_{call.from_user.id}.mp3"
    
    try:
        await generate_audio(final_text, voice_info['id'], output)
        
        # 3-bosqich: Yuklash (Progress: 90%)
        await call.message.edit_text(f"📤 Telegramga yuklanmoqda...\n{get_p_bar(95)}", parse_mode="HTML")
        
        caption = (f"✅ <b>Audio tayyor!</b>\n\n"
                   f"👤 Ovoz: {voice_info['name']}\n"
                   f"⚙️ Rejim: {'Tarjima' if mode=='translate' else 'Asl holatda'}")
        
        await bot.send_audio(call.message.chat.id, FSInputFile(output), caption=caption, parse_mode="HTML")
        update_stats()
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        if os.path.exists(output): os.remove(output)
        await call.message.delete()
        await state.clear()

# --- TEST REJIMI (ALL VOICES) ---
@router.callback_query(F.data.startswith("test_"))
async def test_voices(call: types.CallbackQuery, bot: Bot):
    lang_code = call.data.split("_")[1]
    test_text = VOICES[lang_code]['test_text']
    await call.answer("Ovoz namunalari yuborilmoqda...")
    
    for v_key, v_val in VOICES[lang_code]['voices'].items():
        output = f"test_{v_key}.mp3"
        await generate_audio(test_text, v_val['id'], output)
        await bot.send_audio(call.message.chat.id, FSInputFile(output), caption=f"🎙 {v_val['name']}")
        if os.path.exists(output): os.remove(output)

# --- BACK VA NAVIGATION ---
@router.callback_query(F.data == "back_to_lang")
async def back_to_lang(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mode = data.get("mode", "translate")
    await call.message.edit_text("🌍 Tilni tanlang:", reply_markup=lang_inline_kb(mode=mode))

@router.message(F.text == "🔙 Bosh menyu")
async def back_to_main(message: types.Message):
    await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))
