import edge_tts
import PyPDF2
from docx import Document
from deep_translator import GoogleTranslator
import os
import asyncio

# --- 1. Fayl o'qish funksiyalari ---

def read_pdf(file_path):
    """PDF fayldan matnni ajratib olish"""
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_path)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    except Exception as e:
        return f"Error reading PDF: {e}"
    return text

def read_docx(file_path):
    """Word (DOCX) fayldan matnni ajratib olish"""
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        return f"Error reading DOCX: {e}"
    return text

def read_txt(file_path):
    """Oddiy matn faylini o'qish"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""

# --- 2. Tarjima qilish mantiqi (Chunking bilan) ---

async def translate_text(text, target_lang):
    """
    Matnni bo'laklarga bo'lib, akademik darajada tarjima qilish.
    Bu API cheklovlaridan o'tishga va matnni yo'qotmaslikka yordam beradi.
    """
    translator = GoogleTranslator(source='auto', target=target_lang)
    max_chars = 2500  # Tarjima uchun xavfsiz bo'lak hajmi
    
    # Matnni qatorlarga ajratib, bo'laklarga yig'amiz
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
            # Serverni yuklamaslik uchun qisqa tanaffus
            await asyncio.sleep(0.2) 
        except Exception as e:
            print(f"Tarjimada xato: {e}")
            translated_chunks.append(chunk) # Xato bo'lsa originalni qoldiradi
            
    return "\n\n".join(translated_chunks)

# --- 3. Yangilangan Audio yaratish funksiyasi ---

async def generate_audio(text, voice, output_file):
    """
    Matnni yanada tabiiyroq qilish uchun biroz sekinlashtirilgan 
    parametrlar bilan professional audio yaratish.
    """
    try:
        # rate="-5%" - Nutqni biroz sekinlashtirib, uni insoniyroq va tushunarli qiladi.
        # pitch="+0Hz" - Ovoz tembrini tabiiy holatda saqlaydi.
        # volume="+0%" - Ovoz balandligini standart holatda saqlaydi.
        
        communicate = edge_tts.Communicate(
            text, 
            voice, 
            rate="-5%", 
            pitch="+0Hz"
        )
        
        await communicate.save(output_file)
        return True
    except Exception as e:
        print(f"Audio yaratishda xato yuz berdi: {e}")
        return False

# --- 4. Yordamchi mantiq ---

def get_p_bar(percent):
    """Botda ko'rinadigan progress bar (foiz ko'rsatkichi)"""
    filled = int(percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"<code>{bar}</code> {percent}%"
    
