import os
import tempfile
import asyncio
import json
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

# Loyihangiz modullari
from config import ADMIN_ID, VOICES, GROQ_API_KEY
from database import add_user, update_stats, get_stats, get_all_users
from keyboards import main_menu, admin_menu, lang_inline_kb, voices_inline_kb
from utils import read_pdf, read_docx, read_txt, translate_text, generate_audio

router = Router()
groq_client = Groq(api_key=GROQ_API_KEY)

class BotStates(StatesGroup):
    waiting_for_broadcast = State()

# --- YORDAMCHI FUNKSIYALAR ---

def get_p_bar(percent):
    """Progress bar vizualizatsiyasi: [▓▓▓░░░░░░░] 30%"""
    filled = int(percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"<code>{bar}</code> {percent}%"

async def analyze_text_with_groq(text):
    """Groq AI yordamida matnni tillarga ajratadi (JSON formatida)"""
    prompt = f"""
    Analyze the following text and split it into segments based on language (Uzbek or English).
    Return ONLY a JSON object with a key "segments" containing a list of objects with "text" and "lang" (uz or en).
    Text: {text}
    """
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        result = json.loads(completion.choices[0].message.content)
        return result.get("segments", [])
    except Exception as e:
        logging.error(f"Groq Error: {e}")
        return [{"text": text, "lang": "uz"}] # Xato bo'lsa matnni boricha qaytarish

# --- START VA ADMIN HANDLERLARI ---

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = message.from_user
    add_user(user.id, user.username, user.full_name)
    welcome_text = (f"Assalomu alaykum, <b>{user.full_name}</b>!\n"
                    "Men matnlarni aqlli tahlil qilib, audio yaratuvchi botman.\n"
                    "Matn yuboring yoki fayl yuklang.")
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu(user.id))

@router.message(F.text == "🔐 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin boshqaruv paneli:", reply_markup=admin_menu())

@router.message(F.text == "📊 Statistika")
async def stats_view(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        t, d, u = get_stats()
        text = (f"📈 <b>Bot statistikasi:</b>\n\n"
                f"👥 Foydalanuvchilar: {t}\n"
                f"📅 Bugungi faollik: {d}\n"
                f"🎙 Jami audiolar: {u}")
        await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_request(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:")
        await state.set_state(BotStates.waiting_for_broadcast)

@router.message(BotStates.waiting_for_broadcast)
async def perform_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    users = get_all_users()
    count = 0
    status_msg = await message.answer(f"⏳ Yuborish boshlandi: 0/{len(users)}")
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

# --- MATNNI QABUL QILISH (Progress Bar bilan) ---

@router.message(F.content_type.in_({'text', 'document'}))
async def content_handler(message: types.Message, state: FSMContext, bot: Bot):
    if message.text in ["🔐 Admin Panel", "📊 Statistika", "📢 Xabar yuborish", "🔙 Bosh menyu"]: return
    
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
            if ext == 'pdf': text = read_pdf(tmp.name)
            elif ext == 'docx': text = read_docx(tmp.name)
            elif ext == 'txt': text = read_txt(tmp.name)
            os.remove(tmp.name)
    else:
        text = message.text
        await msg.edit_text(f"⏳ Matn tahlil qilinmoqda...\n{get_p_bar(80)}", parse_mode="HTML")

    if not text or len(text.strip()) < 2:
        await msg.edit_text("❌ Xatolik: Matn bo'sh yoki o'qib bo'lmadi.")
        return

    await msg.edit_text(f"✅ Matn tayyor!\n{get_p_bar(100)}", parse_mode="HTML")
    await state.update_data(text=text)
    await msg.edit_text("🌍 Kerakli tilni yoki <b>Ko'p tilli Mix</b> rejimni tanlang:", 
                        parse_mode="HTML", reply_markup=lang_inline_kb())

# --- AUDIO GENERATSIYA (Groq + Segment Birlashtirish) ---

@router.callback_query(F.data.startswith("lang_"))
async def lang_choice(call: types.CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    await call.message.edit_text("🗣 Ovoz turini tanlang (Erkak/Ayol):", reply_markup=voices_inline_kb(lang))

@router.callback_query(F.data.startswith("voice_"))
async def voice_choice(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    parts = call.data.split("_", 2)
    lang_code, voice_key = parts[1], parts[2]
    
    data = await state.get_data()
    original_text = data.get("text", "")
    output_final = f"final_{call.from_user.id}.mp3"
    
    try:
        # --- AGAR KO'P TILLI REJIM TANLANSA ---
        if lang_code == "multi":
            await call.message.edit_text(f"🤖 Groq AI matnni tahlil qilmoqda...\n{get_p_bar(20)}", parse_mode="HTML")
            segments = await analyze_text_with_groq(original_text)
            temp_files = []
            
            for i, seg in enumerate(segments):
                t_file = f"chunk_{i}_{call.from_user.id}.mp3"
                # Tilga qarab mos ovozni tanlaymiz (voice_key: male_1/female_1)
                t_lang = seg['lang'] if seg['lang'] in VOICES else 'uz'
                v_id = VOICES[t_lang]['voices'][voice_key]['id']
                
                await generate_audio(seg['text'], v_id, t_file)
                temp_files.append(t_file)
                
                prog = 20 + int((i+1)/len(segments) * 60)
                await call.message.edit_text(f"🎙 Audio bo'laklar yozilmoqda ({i+1}/{len(segments)})...\n{get_p_bar(prog)}", parse_mode="HTML")

            # Barcha MP3 bo'laklarni bitta faylga birlashtirish
            with open(output_final, "wb") as outfile:
                for f in temp_files:
                    with open(f, "rb") as infile:
                        outfile.write(infile.read())
                    os.remove(f)
            rejim_label = "Ko'p tilli (Mix)"
            
        else:
            # --- STANDART TARJIMA REJIMI ---
            await call.message.edit_text(f"🌍 Tarjima qilinmoqda...\n{get_p_bar(40)}", parse_mode="HTML")
            final_text = await translate_text(original_text, lang_code)
            
            await call.message.edit_text(f"🎙 Audio yozilmoqda...\n{get_p_bar(70)}", parse_mode="HTML")
            v_id = VOICES[lang_code]['voices'][voice_key]['id']
            await generate_audio(final_text, v_id, output_final)
            rejim_label = f"Tarjima ({lang_code})"

        # Yakuniy natijani yuborish
        await call.message.edit_text(f"📤 Telegramga yuklanmoqda...\n{get_p_bar(95)}", parse_mode="HTML")
        caption = (f"✅ <b>Audio Tayyor!</b>\n\n"
                   f"🎙 Ovoz: {VOICES[lang_code if lang_code!='multi' else 'uz']['voices'][voice_key]['name']}\n"
                   f"⚙️ Rejim: {rejim_label}")
        
        await bot.send_audio(call.message.chat.id, FSInputFile(output_final), caption=caption, parse_mode="HTML")
        update_stats()
        
    except Exception as e:
        await call.message.answer(f"❌ Xatolik: {str(e)}")
    finally:
        if os.path.exists(output_final): os.remove(output_final)
        await call.message.delete()
        await state.clear()

# --- SINOV REJIMI VA NAVIGATSIYA ---

@router.callback_query(F.data.startswith("test_"))
async def test_voices(call: types.CallbackQuery, bot: Bot):
    lang_code = call.data.split("_")[1]
    test_text = VOICES[lang_code]['test_text']
    await call.answer("Ovozlar namunalari yuborilmoqda...")
    
    for v_key, v_val in VOICES[lang_code]['voices'].items():
        out = f"test_{v_key}.mp3"
        await generate_audio(test_text, v_val['id'], out)
        await bot.send_audio(call.message.chat.id, FSInputFile(out), caption=f"🎙 {v_val['name']}")
        if os.path.exists(out): os.remove(out)

@router.callback_query(F.data == "back_to_lang")
async def back_to_lang(call: types.CallbackQuery):
    await call.message.edit_text("🌍 Tilni yoki rejimni tanlang:", reply_markup=lang_inline_kb())

@router.message(F.text == "🔙 Bosh menyu")
async def back_to_main(message: types.Message):
    await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))
