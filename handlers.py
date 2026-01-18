import os
import tempfile
import asyncio
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID, VOICES
from database import add_user, update_stats, get_stats, get_all_users
from keyboards import main_menu, admin_menu, lang_inline_kb, voices_inline_kb
from utils import read_pdf, read_docx, read_txt, translate_text, generate_audio

router = Router()

# Holatlarni boshqarish
class BotStates(StatesGroup):
    waiting_for_broadcast = State()  # Admin xabar yuborishi uchun
    processing_text = State()        # TTS jarayoni uchun

# --- START KOMANDASI ---
@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = message.from_user
    add_user(user.id, user.username, user.full_name)
    welcome_text = (f"Assalomu alaykum, <b>{user.full_name}</b>!\n"
                    "Men matnlarni ovozli xabarga aylantirib beruvchi botman.\n"
                    "Menga matn yuboring yoki fayl (PDF, DOCX, TXT) yuklang.")
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu(user.id))

# --- ADMIN PANEL VA STATISTIKA ---
@router.message(F.text == "🔐 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin panelga xush kelibsiz:", reply_markup=admin_menu())

@router.message(F.text == "📊 Statistika")
async def stats_view(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        t, d, u = get_stats()
        text = (f"📈 <b>Bot statistikasi:</b>\n\n"
                f"👥 Jami foydalanuvchilar: {t}\n"
                f"📅 Bugungi faollik: {d}\n"
                f"🎙 Jami yaratilgan audiolar: {u}")
        await message.answer(text, parse_mode="HTML")

# --- ADMIN BROADCAST (XABAR YUBORISH) ---
@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_request(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni kiriting (matn, rasm, video bo'lishi mumkin):")
        await state.set_state(BotStates.waiting_for_broadcast)

@router.message(BotStates.waiting_for_broadcast)
async def perform_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    users = get_all_users()
    count = 0
    status_msg = await message.answer(f"⏳ Xabar yuborilmoqda: 0/{len(users)}")
    
    for u_id in users:
        try:
            # Har qanday xabar turini (rasm, video, matn) aynan o'zidek nusxalab yuboradi
            await bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
            count += 1
            if count % 10 == 0: # Har 10 ta foydalanuvchida statusni yangilash
                await status_msg.edit_text(f"⏳ Xabar yuborilmoqda: {count}/{len(users)}")
            await asyncio.sleep(0.05) # Telegram blokirovka qilmasligi uchun pauza
        except:
            pass
            
    await message.answer(f"✅ Xabar yuborish tugadi.\nJami yetkazildi: {count} ta foydalanuvchiga.")
    await state.clear()

# --- MATN VA FAYLLARNI QABUL QILISH ---
@router.message(F.content_type.in_({'text', 'document'}))
async def content_handler(message: types.Message, state: FSMContext, bot: Bot):
    # Admin tugmalari bo'lsa, TTS jarayonini boshlamaslik
    if message.text in ["🔐 Admin Panel", "📊 Statistika", "📢 Xabar yuborish", "🔙 Bosh menyu", "ℹ️ Yordam", "📞 Bog'lanish"]:
        return

    # Fayl hajmini tekshirish (20MB = 20 * 1024 * 1024 bytes)
    if message.document and message.document.file_size > 20971520:
        await message.answer("⚠️ Fayl hajmi juda katta! Iltimos, 20MB dan kichik fayl yuboring.")
        return

    msg = await message.answer("⏳ Matn tayyorlanmoqda...")
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
    else:
        text = message.text

    if not text or len(text.strip()) < 2:
        await msg.edit_text("❌ Xatolik: Fayl ichidan matn topilmadi yoki matn juda qisqa.")
        return

    await state.update_data(text=text)
    await msg.edit_text("🌍 Qaysi tilga tarjima qilib o'qib beray?", reply_markup=lang_inline_kb())

# --- TIL VA OVOZ TANLASH ---
@router.callback_query(F.data.startswith("lang_"))
async def lang_choice(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text("🗣 Ovozni tanlang:", reply_markup=voices_inline_kb(lang))

@router.callback_query(F.data.startswith("voice_"))
async def voice_choice(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    parts = call.data.split("_")
    lang_code = parts[1]
    voice_key = parts[2]
    
    voice_info = VOICES[lang_code]['voices'][voice_key]
    data = await state.get_data()
    original_text = data.get("text", "")
    
    await call.message.edit_text(f"🔄 <b>{voice_info['name']}</b> ovozida tayyorlanmoqda...", parse_mode="HTML")
    
    # Tarjima va Ovoz berish
    translated = await translate_text(original_text, lang_code)
    output_file = f"audio_{call.from_user.id}.mp3"
    
    try:
        await generate_audio(translated, voice_info['id'], output_file)
        await bot.send_audio(
            chat_id=call.message.chat.id,
            audio=FSInputFile(output_file),
            caption=f"✅ <b>Tayyor!</b>\n🎙 Ovoz: {voice_info['name']}\n🌍 Til: {VOICES[lang_code]['label']}",
            parse_mode="HTML"
        )
        update_stats()
    except Exception as e:
        await call.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)
        await call.message.delete()
        await state.clear()

# --- BOSHQA TUGMALAR ---
@router.message(F.text == "🔙 Bosh menyu")
async def back_to_main(message: types.Message):
    await message.answer("Bosh menyu", reply_markup=main_menu(message.from_user.id))

@router.message(F.text == "ℹ️ Yordam")
async def help_cmd(message: types.Message):
    await message.answer("Siz matn yoki fayl yuborasiz, men uni tarjima qilib ovozli xabar (MP3) ko'rinishida qaytaraman.")
