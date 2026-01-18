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

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = message.from_user
    add_user(user.id, user.username, user.full_name)
    await message.answer(f"Assalomu alaykum, {user.full_name}!", reply_markup=main_menu(user.id))

# --- ADMIN PANEL ---
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
    await message.answer(f"⏳ Yuborish boshlandi...")
    for u_id in users:
        try:
            await bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Tugadi. {count} ta foydalanuvchiga yetkazildi.")
    await state.clear()

# --- TTS JARAYONI ---
@router.message(F.content_type.in_({'text', 'document'}))
async def content_handler(message: types.Message, state: FSMContext, bot: Bot):
    if message.text in ["🔐 Admin Panel", "📊 Statistika", "📢 Xabar yuborish", "🔙 Bosh menyu"]: return
    
    if message.document and message.document.file_size > 20*1024*1024:
        await message.answer("❌ Fayl 20MB dan katta bo'lmasligi kerak.")
        return

    msg = await message.answer("⏳ Matn o'qilmoqda...")
    text = ""
    if message.document:
        file = await bot.get_file(message.document.file_id)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            await bot.download_file(file.file_path, tmp.name)
            ext = message.document.file_name.split('.')[-1].lower()
            if ext == 'pdf': text = await read_pdf(tmp.name)
            elif ext == 'docx': text = await read_docx(tmp.name)
            elif ext == 'txt': text = await read_txt(tmp.name)
            os.remove(tmp.name)
    else: text = message.text

    if not text:
        await msg.edit_text("❌ Matn topilmadi.")
        return

    await state.update_data(text=text)
    await msg.edit_text("🌍 Tilni tanlang:", reply_markup=lang_inline_kb())

@router.callback_query(F.data.startswith("lang_"))
async def lang_choice(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text("🗣 Ovozni tanlang:", reply_markup=voices_inline_kb(lang))

@router.callback_query(F.data.startswith("voice_"))
async def voice_choice(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    parts = call.data.split("_")
    voice_id = VOICES[parts[1]]['voices'][parts[2]]['id']
    data = await state.get_data()
    await call.message.edit_text("🔄 Tayyorlanmoqda...")
    
    translated = await translate_text(data['text'], parts[1])
    output = f"audio_{call.from_user.id}.mp3"
    await generate_audio(translated, voice_id, output)
    
    await bot.send_audio(call.message.chat.id, FSInputFile(output), caption="✅ Tayyor!")
    update_stats()
    if os.path.exists(output): os.remove(output)
    await call.message.delete()
    await state.clear()

@router.message(F.text == "🔙 Bosh menyu")
async def back(message: types.Message):
    await message.answer("Bosh menyu", reply_markup=main_menu(message.from_user.id))
