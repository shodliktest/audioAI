import edge_tts
import PyPDF2
from docx import Document
from deep_translator import GoogleTranslator
import os
import asyncio

# --- Fayl o'qish funksiyalari (O'zgartirilmagan) ---

def read_pdf(file_path):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_path)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    except Exception as e:
        return f"Error: {e}"
    return text

def read_docx(file_path):
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        return f"Error: {e}"
    return text

def read_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""

# --- Akademik Tarjima va TTS Funksiyalari (Yangilangan mantiq bilan) ---

async def translate_text(text, target_lang):
    """
    Matnni bo'laklarga bo'lib, akademik darajada (to'liq) tarjima qilish funksiyasi.
    Hech qanday qisqartirishlarsiz, barcha so'zlarni qamrab oladi.
    """
    if not text or len(text.strip()) == 0:
        return ""

    translator = GoogleTranslator(source='auto', target=target_lang)
    
    # Deep-translator va API barqarorligi uchun matnni 2500 belgidan bo'laklaymiz.
    # Bu akademik aniqlikni va xatosiz ishlashni ta'minlaydi.
    max_chars = 2500
    
    # Matnni bo'laklarga bo'lish (gaplar buzilmasligi uchun qatorlar bo'yicha)
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) < max_chars:
            current_chunk += line + "\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = line + "\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())

    translated_chunks = []
    
    for chunk in chunks:
        if not chunk.strip():
            continue
        try:
            # Har bir bo'lakni alohida tarjima qilish
            res = translator.translate(chunk)
            translated_chunks.append(res)
            # API cheklovlariga tushib qolmaslik uchun qisqa tanaffus
            await asyncio.sleep(0.1) 
        except Exception as e:
            print(f"Tarjimada xato: {e}")
            # Xatolik bo'lsa matnni o'zini qoldiradi (yo'qotmaslik uchun)
            translated_chunks.append(chunk) 
            
    # Barcha tarjima qilingan bo'laklarni birlashtirish
    return "\n\n".join(translated_chunks)

async def generate_audio(text, voice, output_file):
    """
    Matnni audio faylga aylantirish (Edge TTS orqali).
    """
    try:
        # Agar matn juda uzun bo'lsa ham edge-tts uni qayta ishlay oladi
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        return True
    except Exception as e:
        print(f"Audio yaratishda xato: {e}")
        return False
    
