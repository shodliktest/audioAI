import os
import streamlit as st

# Tokenni olish (Streamlit Secrets yoki oddiy string)
try:
    BOT_TOKEN = st.secrets["BOT_TOKEN"]
except:
    BOT_TOKEN = "SIZNING_BOT_TOKENINGIZ_BU_YERGA"

ADMIN_ID = 1416457518
DB_FILE = "bot_database.db"

# --- KENGAYTIRILGAN OVOZLAR BAZASI ---
# Har bir til uchun bir nechta variantlar
VOICES = {
   "multi": {
        "label": "🌐 Ko'p tilli (Mix)",
        "voices": {
            "female_1": {"id": "en-US-AvaMultilingualNeural", "name": "Ava (Ayol - Ko'p tilli)", "gender": "Ayol"},
            "male_1": {"id": "en-US-AndrewMultilingualNeural", "name": "Andrew (Erkak - Ko'p tilli)", "gender": "Erkak"},
        },
        "test_text": "Assalomu alaykum! My name is Andrew. I can read both Uzbek and English perfectly."
    },
    "uz": {
        "label": "🇺🇿 O'zbekcha",
        "voices": {
            "female_1": {"id": "uz-UZ-MadinaNeural", "name": "Madina (Ayol)", "gender": "Ayol"},
            "male_1": {"id": "uz-UZ-SardorNeural", "name": "Sardor (Erkak)", "gender": "Erkak"},
        },
        "test_text": "Bu sinov rejimi. Ovoz sifati va intonatsiyasini tekshirishingiz mumkin."
    },
    "en": {
        "label": "🇺🇸 English",
        "voices": {
            "male_1": {"id": "en-US-ChristopherNeural", "name": "Christopher (Erkak - Jiddiy)", "gender": "Erkak"},
            "male_2": {"id": "en-US-GuyNeural", "name": "Guy (Erkak - Tabiiy)", "gender": "Erkak"},
            "female_1": {"id": "en-US-AriaNeural", "name": "Aria (Ayol - Yoqimli)", "gender": "Ayol"},
            "female_2": {"id": "en-US-JennyNeural", "name": "Jenny (Ayol - Ravon)", "gender": "Ayol"},
             "robot": {"id": "en-US-AnaNeural", "name": "Ana (Ayol - Bolalar uchun)", "gender": "Bola/Robot"} 
        },
        "test_text": "This is a test mode. You can check the voice quality and intonation."
    },
    "ru": {
        "label": "🇷🇺 Русский",
        "voices": {
            "male_1": {"id": "ru-RU-DmitryNeural", "name": "Дмитрий (Erkak)", "gender": "Erkak"},
            "female_1": {"id": "ru-RU-SvetlanaNeural", "name": "Светлана (Ayol)", "gender": "Ayol"},
        },
        "test_text": "Это тестовый режим. Вы можете проверить качество голоса и интонацию."
    }
    # Boshqa tillarni ham shu formatda qo'shishingiz mumkin
}

