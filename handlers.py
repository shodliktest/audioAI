import os
import tempfile
import asyncio
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

# --- YORDAMCHI FUNKSIYALAR ---

def get_p_bar(percent):
    """Progress bar vizualizatsiyasi uchun: [▓▓▓░░░░░░░] 30%"""
    filled = int(percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"<code>{bar}</code> {percent}%"

# --- START VA ADMIN HANDLERLARI ---

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = message.from_user
    add_user(user.id, user.username, user.full_name)
    await message.answer(
        f"Assalomu alaykum, <b>{user.full_name}</b>!\nMatn yuboring yoki fayl yuklang.",
        parse_mode="HTML",
        reply_markup=main_menu(user.id)
    )

@router.message(F.text == "🔐 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin boshqaruv paneli:", reply_markup=admin_menu())

@router.message(F.text == "📊 Statistika")
async def stats_view(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        t, d, u = get_stats()
        await message.answer(f"👥 Jami foydalanuvchilar: {t}\n📅 Bugun: {d}\n🎙 Jami audiolar: {u}")

@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_request(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:")
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
            if count % 10 == 0:
                await status_msg.edit_text(f"⏳ Yuborilmoqda: {count}/{len(users)}")
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Tugadi. {count} ta foydalanuvchiga yetkazildi.")
    await state.clear()

# --- REJIMLARNI BOSHQARISH ---

@router.callback_query(F.data == "set_mode_original")
async def set_mode_original(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(mode="original")
    await call.message.edit_text(
        "<b>Asl holatda (Tarjimasiz) o'qish:</b>\nOvoz tilini tanlang:",
        parse_mode="HTML",
        reply_markup=lang_inline_kb(mode="original")
    )

@router.callback_query(F.data == "set_mode_translate")
async def set_mode_translate(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(mode="translate")
    await call.message.edit_text(
        "<b>Tarjima rejimi:</b>\nTilni tanlang:",
        parse_mode="HTML",
        reply_markup=lang_inline_kb(mode="translate")
    )

# --- MATNNI QABUL QILISH (FOIZLAR BILAN) ---

@router.message(F.content_type.in_({'text', 'document'}))
async def content_handler(message: types.Message, state: FSMContext, bot: Bot):
    if message.text in ["🔐 Admin Panel", "📊 Statistika", "📢 Xabar yuborish", "🔙 Bosh menyu"]:
        return
    
    msg = await message.answer(f"⏳ Fayl/Matn o'qilmoqda...\n{get_p_bar(10)}", parse_mode="HTML")
    
    text = ""
    if message.document:
        if message.document.file_size > 20*1024*1024:
            await msg.edit_text("❌ Fayl 20MB dan katta bo'lmasligi kerak.")
            return

        file = await bot.get_file(message.document.file_id)
        await msg.edit_text(f"⏳ Fayl serverga yuklanmoqda...\n{get_p_bar(40)}", parse_mode="HTML")
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            await bot.download_file(file.file_path, tmp.name)
            await msg.edit_text(f"⏳ Matn ajratib olinmoqda...\n{get_p_bar(70)}", parse_mode="HTML")
            
            ext = message.document.file_name.split('.')[-1].lower()
            if ext == 'pdf': text = await read_pdf(tmp.name)
            elif ext == 'docx': text = await read_docx(tmp.name)
            elif ext == 'txt': text = await read_txt(tmp.name)
            os.remove(tmp.name)
    else:
        text = message.text
        await msg.edit_text(f"⏳ Matn tahlil qilinmoqda...\n{get_p_bar(80)}", parse_mode="HTML")

    if not text or len(text.strip()) < 2:
        await msg.edit_text("❌ Xatolik: Matn topilmadi yoki juda qisqa.")
        return

    await msg.edit_text(f"✅ Matn tayyor!\n{get_p_bar(100)}", parse_mode="HTML")
    await asyncio.sleep(0.5)

    await state.update_data(text=text, mode="translate") # Standart rejim: Tarjima
    await msg.edit_text("🌍 Kerakli tilni tanlang:", reply_markup=lang_inline_kb())

# --- CALLBACKLAR (TIL, OVOZ VA AUDIO GENERATSIYA) ---

@router.callback_query(F.data.startswith("lang_"))
async def lang_choice(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text("🗣 Ovozni tanlang:", reply_markup=voices_inline_kb(lang))

@router.callback_query(F.data.startswith("voice_"))
async def voice_choice(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    # split("_", 2) female_1 kabi kalitlarni buzmaslik uchun
    parts = call.data.split("_", 2)
    lang_code, voice_key = parts[1], parts[2]
    
    data = await state.get_data()
    mode = data.get("mode", "translate")
    original_text = data.get("text", "")
    voice_info = VOICES[lang_code]['voices'][voice_key]
    
    # 1-qadam: Tarjima
    await call.message.edit_text(f"⏳ Jarayon boshlandi...\n{get_p_bar(10)}", parse_mode="HTML")
    
    if mode == "translate":
        await call.message.edit_text(f"⏳ Tarjima qilinmoqda...\n{get_p_bar(30)}", parse_mode="HTML")
        final_text = await translate_text(original_text, lang_code)
    else:
        final_text = original_text
    
    # 2-qadam: Audio yaratish
    await call.message.edit_text(f"🎙 Audio yozilmoqda ({voice_info['name']})...\n{get_p_bar(60)}", parse_mode="HTML")
    output = f"audio_{call.from_user.id}.mp3"
    
    try:
        await generate_audio(final_text, voice_info['id'], output)
        
        # 3-qadam: Yuklash
        await call.message.edit_text(f"📤 Telegramga yuklanmoqda...\n{get_p_bar(90)}", parse_mode="HTML")
        
        caption = (f"✅ <b>Tayyor!</b>\n\n"
                   f"🎙 Ovoz: {voice_info['name']}\n"
                   f"⚙️ Rejim: {'Tarjima' if mode=='translate' else 'Asl holatda'}")
        
        await bot.send_audio(
            call.message.chat.id, 
            FSInputFile(output), 
            caption=caption,
            parse_mode="HTML"
        )
        update_stats()
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        if os.path.exists(output): os.remove(output)
        await call.message.delete()
        await state.clear()

@router.callback_query(F.data.startswith("test_"))
async def test_voices(call: types.CallbackQuery, bot: Bot):
    lang_code = call.data.split("_")[1]
    test_text = VOICES[lang_code]['test_text']
    await call.answer("Ovozlar namunalari yuborilmoqda...")
    
    for v_key, v_val in VOICES[lang_code]['voices'].items():
        output = f"test_{v_key}.mp3"
        await generate_audio(test_text, v_val['id'], output)
        await bot.send_audio(call.message.chat.id, FSInputFile(output), caption=f"🎙 {v_val['name']}")
        if os.path.exists(output): os.remove(output)

@router.callback_query(F.data == "back_to_lang")
async def back_to_lang(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mode = data.get("mode", "translate")
    await call.message.edit_text("🌍 Tilni tanlang:", reply_markup=lang_inline_kb(mode=mode))

@router.message(F.text == "🔙 Bosh menyu")
async def back(message: types.Message):
    await message.answer("Bosh menyu", reply_markup=main_menu(message.from_user.id))
