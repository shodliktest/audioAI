import streamlit as st

try:
    BOT_TOKEN = st.secrets["BOT_TOKEN"]
except (KeyError, FileNotFoundError):
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

ADMIN_ID = 1416457518
DB_FILE = "bot_database.db"

VOICES = {
    "multi": {
        "label": "🌐 Ko'p tilli (Smart Mix) ➡️",
        "voices": {
            "female_1": {"id": "uz-UZ-MadinaNeural", "name": "Madina & Global (Mix)", "gender": "Ayol"},
            "male_1": {"id": "uz-UZ-SardorNeural", "name": "Sardor & Global (Mix)", "gender": "Erkak"},
        }
    },
    "uz": {
        "label": "🇺🇿 O'zbekcha",
        "voices": {
            "female_1": {"id": "uz-UZ-MadinaNeural", "name": "Madina", "gender": "Ayol"},
            "male_1": {"id": "uz-UZ-SardorNeural", "name": "Sardor", "gender": "Erkak"},
        },
        "test_text": "Bu o'zbek tili uchun sinov audiosi."
    },
        "en": {
        "label": "🇺🇸 English",
        "voices": {
            "female_1": {"id": "en-US-AvaNeural", "name": "Ava (Premium)", "gender": "Ayol"},
            "male_1": {"id": "en-US-AndrewNeural", "name": "Andrew (Premium)", "gender": "Erkak"},
            "female_2": {"id": "en-GB-SoniaNeural", "name": "Sonia (British)", "gender": "Ayol"},
            "male_2": {"id": "en-GB-RyanNeural", "name": "Ryan (British)", "gender": "Erkak"},
        },
        "test_text": "This is a high-quality neural voice for English."
    },

    "tr": {
        "label": "🇹🇷 Turkcha",
        "voices": {
            "female_1": {"id": "tr-TR-EmelNeural", "name": "Emel", "gender": "Ayol"},
            "male_1": {"id": "tr-TR-AhmetNeural", "name": "Ahmet", "gender": "Erkak"},
        },
        "test_text": "Bu Türk dili için bir test sesidir."
    },
    "ko": {
        "label": "🇰🇷 Koreyscha",
        "voices": {
            "female_1": {"id": "ko-KR-SunHiNeural", "name": "Sun-Hi", "gender": "Ayol"},
            "male_1": {"id": "ko-KR-BongJinNeural", "name": "Bong-Jin", "gender": "Erkak"},
        },
        "test_text": "이것은 한국어 테스트 오디오입니다."
    },
    "ar": {
        "label": "🇸🇦 Arabcha",
        "voices": {
            "female_1": {"id": "ar-SA-ZariyahNeural", "name": "Zariyah", "gender": "Ayol"},
            "male_1": {"id": "ar-SA-HamedNeural", "name": "Hamed", "gender": "Erkak"},
        },
        "test_text": "هذا تسجيل صوتي تجريبي للغة العربية"
    },
    "ru": {
        "label": "🇷🇺 Русский",
        "voices": {
            "female_1": {"id": "ru-RU-SvetlanaNeural", "name": "Светлана", "gender": "Ayol"},
            "male_1": {"id": "ru-RU-DmitryNeural", "name": "Дмитрий", "gender": "Erkak"},
        },
        "test_text": "Это тестовое аудио для русского языка."
    }
}

