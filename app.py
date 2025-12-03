import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from pptx import Presentation
from gtts import gTTS
import tempfile
import os
import json
import time

# --- 1. INSTÄLLNINGAR (Måste vara först) ---
st.set_page_config(page_title="Jag Lär Mig", page_icon="📖", layout="wide")

# --- 2. STARTA MINNET (Session State) ---
# Vi initierar minnet direkt för att undvika fel
if "subjects" not in st.session_state:
    st.session_state.subjects = {"Allmänt": {"material": "", "history": []}}

if "current_subject" not in st.session_state:
    st.session_state.current_subject = list(st.session_state.subjects.keys())[0]

if "flashcards" not in st.session_state:
    st.session_state.flashcards = {}

# --- 3. BAKGRUNDSBILDER ---
BACKGROUND_MAP = {
    "NO": "url('https://images.unsplash.com/photo-1532094349884-543bc11b234d?q=80&w=2500&auto=format&fit=crop')",
    "Geografi": "url('https://images.unsplash.com/photo-1524661135-423995f22d0b?q=80&w=2500&auto=format&fit=crop')",
    "Idrott": "url('https://images.unsplash.com/photo-1461896836934-ffe607ba8211?q=80&w=2500&auto=format&fit=crop')",
    "Matte": "url('https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=2500&auto=format&fit=crop')",
    "Allmänt": "url('https://images.unsplash.com/photo-1457369804613-52c61a468e7d?q=80&w=2500&auto=format&fit=crop')",
}

def set_background(subject_name):
    bg_url = BACKGROUND_MAP.get(subject_name, BACKGROUND_MAP['Allmänt'])
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: {bg_url};
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            transition: background-image 0.5s ease-in-out;
        }}
        /* Gör texten mer läsbar mot bakgrunden med en halvgenomskinlig ruta */
        .main .block-container {{
            background-color: rgba(0, 0, 0, 0.6);
            padding: 2rem;
            border-radius: 10px;
        }}
        h1, h2, h3, p, div, span {{
            color: white !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Kör bakgrundsfunktionen
set_background(st.session_state.current_subject)

# --- 4. FUNKTIONER ---

def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            text += page.extract_text()
    except Exception:
        text = "Kunde inte läsa PDF."
    return text

def extract_text_from_pptx(pptx_file):
    text = ""
    try:
        prs = Presentation(pptx_file)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
    except Exception:
        text = "Kunde inte läsa PowerPoint."
    return text

def generate_speech_simple(text):
    try:
        if not text.strip():
            return None
        tts = gTTS(text=text, lang='sv')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"Ljudfel: {e}")
        return None

def get_gemini_response(prompt, context, api_key):
    if not api_key: 
        return "⚠️ Ingen API-nyckel hittades i Secrets."
    
    try:
        genai.configure(api_key=api_key)
        # Använder gemini-pro för stabilitet om flash strular
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        full_prompt = (
            "Du är en pedagogisk lärare i appen 'Jag Lär Mig'. "
            "Svara på svenska. Håll dig till materialet nedan.\n\n"
            f"MATERIAL:\n{context}\n\n"
            f"UPPGIFT: {prompt}"
        )
        response = model.generate_content(full_prompt)
        return response.text
        
    except Exception as e:
        if "API_KEY_INVALID" in str(e) or "400" in str(e):
            return "❌ API-nyckeln avvisades. Kontrollera Secrets!"
        elif "NotFound" in str(e):
            return "❌ Modellen hittades inte. Försök byta modell i koden."
        else:
            return f"Ett fel uppstod: {str(e)}"

# --- 5. SIDOPANEL ---

with st.sidebar:
    st.title("📖 Jag Lär Mig")
    
    # Hämta nyckel från Secrets
    api_key = st.secrets.get("GEMINI_API_KEY")
    
    if api_key:
        st.success(f"✅ Nyckel laddad! (Start: {api_key[:4]}...)")
    else:
        st.error("❌ Ingen nyckel i Secrets!")
    
    st.divider()
    
    st.subheader("Välj Ämne")
    
    # Hämta lista på ämnen
    subject_list = list(st.session_state.subjects.keys())
    
    # Hitta index för nuvarande ämne
    try:
        current_index = subject_list.index(st.session_state.current_subject)
    except ValueError:
        current_index = 0
        st.session_state.current_subject = subject_list[0]

    # Väljaren
    selected_sub = st.selectbox("Ämne:", subject_list, index=current_index)
    
    # Byt bakgrund om ämnet ändras
    if selected_sub != st.session_state.current_subject:
        st.session_state.current_subject = selected_sub
        st.rerun()

    # Skapa nytt ämne
    new_sub = st.text_input("Nytt ämne (t.ex. Historia):")
    if st.button("Skapa Mapp") and new_sub:
        if new_sub not in st.session_state.subjects:
            st.session_state.subjects[new_sub] = {"material": "", "history": []}
            st.session_state.current_subject = new_sub
