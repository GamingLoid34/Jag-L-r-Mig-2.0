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

# --- 2. STARTA MINNET (Session State) - FIXAR FELET ---
# Vi måste garantera att dessa variabler finns innan vi använder dem
if "subjects" not in st.session_state:
    st.session_state.subjects = {"Allmänt": {"material": "", "history": []}}

if "current_subject" not in st.session_state:
    # Sätter standardvärdet till det första ämnet i listan
    st.session_state.current_subject = list(st.session_state.subjects.keys())[0]

if "flashcards" not in st.session_state:
    st.session_state.flashcards = {}

# --- 3. BAKGRUNDSBILDER ---
BACKGROUND_MAP = {
    "NO": "url('https://images.unsplash.com/photo-1582719478253-6ce7ebdf11c8?q=80&w=2500&auto=format&fit=crop')",
    "Geografi": "url('https://images.unsplash.com/photo-1541334311090-344070a7b055?q=80&w=2500&auto=format&fit=crop')",
    "Idrott": "url('https://images.unsplash.com/photo-1517590806450-482a2af16719?q=80&w=2500&auto=format&fit=crop')",
    "Matte": "url('https://images.unsplash.com/photo-1596495689108-bc31c626456f?q=80&w=2500&auto=format&fit=crop')",
    "Allmänt": "url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=2500&auto=format&fit=crop')",
}

def set_background(subject_name):
    # Hämtar URL, om ämnet inte finns i listan används "Allmänt"
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
        /* Gör texten mer läsbar mot bakgrunden */
        .stMarkdown, .stHeader, .stTitle, p, h1, h2, h3 {{
            text-shadow: 0px 0px 5px rgba(0,0,0,0.5);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Kör bakgrundsfunktionen direkt
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
    # Kontrollera nyckeln
    if not api_key: 
        return "⚠️ Ingen API-nyckel hittades i Secrets."
    
    try:
        genai.configure(api_key=api_key)
        
        # Vi använder 'gemini-1.5-flash' (eller 'gemini-pro' om flash strular för ditt konto)
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
        # Fånga fel för att hjälpa till med felsökning
        if "API_KEY_INVALID" in str(e) or "400" in str(e):
            return "❌ API-nyckeln avvisades av Google. Kontrollera Secrets!"
        elif "NotFound" in str(e):
            return "❌ Modellen hittades inte. Försök byta till 'gemini-pro' i koden."
        else:
            return f"Ett tekniskt fel uppstod: {str(e)}"

# --- 5. SIDOPANEL & NAVIGERING ---

with st.sidebar:
    st.title("📖 Jag Lär Mig")
    
    # Hämta nyckel från Secrets
    api_key = st.secrets.get("GEMINI_API_KEY")
    
    # --- DIAGNOS: VISA OM NYCKEL FINNS ---
    if api_key:
        # HÄR VAR FELET: F-strängen måste vara hel
        st.success(f"✅ Nyckel laddad! (Börjar på: {api_key[:4]}...)")
    else:
        st.error("❌ Ingen nyckel i Secrets!")
        st.info("Lägg till GEMINI_API_KEY i dina Streamlit Secrets.")
    
    st.divider()
    
    st.subheader("Välj Ämne")
    
    # Hämta lista på ämnen
    subject_list = list(st.session_state.subjects.keys())
    
    # Se till att index är giltigt
    try:
        current_index = subject_list.index(st.session_state.current_subject)
    except ValueError:
        current_index = 0
        st.session_state.current_subject = subject_list[0]

    # Väljaren
    selected_sub = st.selectbox("Ämne:", subject_list, index=current_index)
    
    # Om användaren byter ämne, uppdatera state och ladda om för att byta bakgrund
    if selected_sub != st.session_state.current_subject:
        st.session_state.current_subject = selected_sub
        st.rerun()

    # Skapa nytt ämne
    new_sub = st.text_input("Nytt ämne (t.ex. Historia):")
    if st.button("Skapa Mapp") and new_sub:
        if new_sub not in st.session_state.subjects:
            st.session_state.subjects[new_sub] = {"material": "", "history": []}
            st.session_state.current_subject = new_sub
            st.success(f"Skapade {new_sub}!")
            st.rerun()

    st.divider()
    
    # Uppladdning
    st.subheader(f"Ladda upp till {st.session_state.current_subject}")
    uploaded_files = st.file_uploader("Filer (PDF, PPTX)", accept_multiple_files=True)
    
    if st.button("Spara Filer"):
        current_data = st.session_state.subjects[st.session_state.current_subject]["material"]
        for file in uploaded_files:
            if file.name.endswith(".pdf"):
                current_data += f"\n--- {file.name} ---\n" + extract_text_from_pdf(file)
            elif file.name.endswith(".pptx"):
                current_data += f"\n--- {file.name} ---\n" + extract_text_from_pptx(file)
        
        st.session_state.subjects[st.session_state.current_subject]["material"] = current_data
        st.success("Material sparat!")
