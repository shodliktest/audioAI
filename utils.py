import edge_tts
import PyPDF2
from docx import Document
from deep_translator import GoogleTranslator
import os

# --- Fayl o'qish ---
def read_pdf(file_path):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
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
    except:
        return ""

# --- Tarjima va TTS ---
async def translate_text(text, target_lang):
    if len(text) > 4500:
        text = text[:4500] + "..."
    translator = GoogleTranslator(source='auto', target=target_lang)
    return translator.translate(text)

async def generate_audio(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice, rate="-10%")
    await communicate.save(output_file)
