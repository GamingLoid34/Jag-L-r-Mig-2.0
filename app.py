import streamlit as st 
import google.generativeai as genai 
from PyPDF2 import PdfReader 
from pptx import Presentation 
from gtts import gTTS 
import tempfile 
import os 
import json 
import re
 
# --- 1. INSTÄLLNINGAR (Måste vara först) --- 
st.set_page_config(page_title="Jag Lär Mig", page_icon="📖", layout="wide") 
 
# --- 2. STARTA MINNET (Session State) --- 
if "subjects" not in st.session_state: 
    st.session_state.subjects = {"Allmänt": {"material": "", "history": []}} 
 
if "current_subject" not in st.session_state: 
    st.session_state.current_subject = list(st.session_state.subjects.keys())[0] 
 
if "flashcards" not in st.session_state: 
    st.session_state.flashcards = {} 
 
# --- 3. BAKGRUNDSBILDER & DESIGN --- 
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
        /* Bakgrundsbild */ 
        .stApp {{ 
            background-image: {bg_url}; 
            background-size: cover; 
            background-repeat: no-repeat; 
            background-attachment: fixed; 
            transition: background-image 0.5s ease-in-out; 
        }} 
         
        /* Mörkare ruta bakom texten för läsbarhet */ 
        .main .block-container {{ 
            background-color: rgba(0, 0, 0, 0.75); /* 75% svart */ 
            padding: 2rem; 
            border-radius: 15px; 
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5); 
        }} 
 
        /* Textfärger - Enbart rubriker och paragrafer blir vita */ 
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {{ 
            color: white !important; 
        }} 
 
        /* Fixa knapparna så de syns! */ 
        .stButton > button {{ 
            background-color: #ff4b4b !important; /* Röd färg */ 
            color: white !important; /* Vit text */ 
            border: none; 
            font-weight: bold; 
        }} 
        .stButton > button:hover {{ 
            background-color: #ff2b2b !important; /* Mörkare röd vid hover */ 
        }} 
         
        /* Fixa textrutor (Input fields) */ 
        .stTextInput > div > div > input {{ 
            color: black !important; 
            background-color: white !important; 
        }} 
        .stTextArea > div > div > textarea {{ 
            color: black !important; 
            background-color: white !important; 
        }} 
        </style> 
        """, 
        unsafe_allow_html=True 
    ) 
 
# Kör designfunktionen 
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
        # Använder gemini-pro för stabilitet 
        model = genai.GenerativeModel('gemini-pro')
         
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
     
    api_key = st.secrets.get("GEMINI_API_KEY") 
     
    if api_key: 
        st.success(f"✅ Nyckel OK! ({api_key[:4]}...)") 
    else: 
        st.error("❌ Ingen nyckel i Secrets!") 
     
    st.divider() 
     
    st.subheader("Välj Ämne") 
     
    subject_list = list(st.session_state.subjects.keys()) 
     
    try: 
        current_index = subject_list.index(st.session_state.current_subject) 
    except ValueError: 
        current_index = 0 
        st.session_state.current_subject = subject_list[0] 
 
    selected_sub = st.selectbox("Ämne:", subject_list, index=current_index) 
     
    if selected_sub != st.session_state.current_subject: 
        st.session_state.current_subject = selected_sub 
        st.rerun() 
 
    new_sub = st.text_input("Nytt ämne (t.ex. Historia):") 
    if st.button("Skapa Mapp") and new_sub: 
        if new_sub not in st.session_state.subjects: 
            st.session_state.subjects[new_sub] = {"material": "", "history": []} 
            st.session_state.current_subject = new_sub 
            st.success(f"Skapade {new_sub}!") 
            st.rerun() 
 
    st.divider() 
     
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
        st.success(f"Sparade filer!") 
        st.rerun() 
 
# --- 6. HUVUDVY --- 
 
st.header(f"Studerar: {st.session_state.current_subject}") 
 
active_subject_data = st.session_state.subjects[st.session_state.current_subject] 
material_text = active_subject_data["material"] 
 
if not material_text: 
    st.info("📂 Mappen är tom. Ladda upp filer i menyn till vänster för att se verktygen!") 
else: 
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Läs & Redigera", "🧠 Förhör Mig", "🃏 Flashcards", "🎧 Lyssna"]) 
 
    # FLIK 1 
    with tab1: 
        st.caption("Ditt material:") 
        edited_text = st.text_area("Text", material_text, height=400) 
         
        col_save, col_split, col_clear = st.columns(3) 
        if col_save.button("Spara ändringar"): 
            st.session_state.subjects[st.session_state.current_subject]["material"] = edited_text 
            st.success("Sparat!") 
            st.rerun() 
             
        if col_split.button("✨ Dela upp i kapitel"): 
            with st.spinner("AI arbetar..."): 
                res = get_gemini_response("Dela upp texten i tydliga kapitel med rubriker.", edited_text, api_key) 
                st.markdown(res)

        if col_clear.button("🗑️ Rensa Material"):
            # Kolla om bekräftelsen gäller för just detta ämne
            if st.session_state.get("confirm_clear") == st.session_state.current_subject:
                st.session_state.subjects[st.session_state.current_subject]["material"] = ""
                st.session_state.confirm_clear = None # Återställ
                st.success("Materialet har rensats!")
                st.rerun()
            else:
                # Spara ämnets namn för bekräftelse
                st.session_state.confirm_clear = st.session_state.current_subject
                st.warning(f"Är du säker på att du vill rensa materialet för '{st.session_state.current_subject}'? Klicka igen för att bekräfta.")
                st.rerun()
 
    # FLIK 2 
    with tab2: 
        col1, col2 = st.columns(2) 
        if col1.button("📝 Skapa Prov"): 
            with st.spinner("Skapar prov..."): 
                res = get_gemini_response("Skapa ett prov med 3 frågor och facit.", material_text, api_key) 
                st.markdown(res) 
         
        if col2.button("📋 Sammanfatta"): 
            with st.spinner("Sammanfattar..."): 
                res = get_gemini_response("Sammanfatta det viktigaste.", material_text, api_key) 
                st.markdown(res) 
 
        st.divider() 
        
        # Visa historik
        for msg in active_subject_data.get("history", []):
            st.chat_message(msg["role"]).write(msg["content"])

        user_msg = st.chat_input("Fråga din AI-lärare...") 
        if user_msg: 
            st.chat_message("user").write(user_msg) 
            active_subject_data["history"].append({"role": "user", "content": user_msg})

            with st.spinner("Tänker..."): 
                ai_msg = get_gemini_response(user_msg, material_text, api_key) 
                st.chat_message("assistant").write(ai_msg) 
                active_subject_data["history"].append({"role": "assistant", "content": ai_msg})
 
    # FLIK 3 
    with tab3: 
        st.subheader("Plugga begrepp") 
        if st.button("Generera nya kort"): 
            with st.spinner("Skapar kort..."): 
                prompt = "Skapa 3 flashcards i JSON-format: [{'question': '...', 'answer': '...'}, ...]" 
                json_res = get_gemini_response(prompt, material_text, api_key) 
                try:
                    # Försök hitta JSON-blocket med re
                    match = re.search(r"```json\s*(\[.*\])\s*```", json_res, re.DOTALL)
                    if match:
                        clean_json = match.group(1)
                        cards = json.loads(clean_json)
                        st.session_state.flashcards[st.session_state.current_subject] = cards
                        st.success("Kort skapade!")
                    else:
                        # Fallback om re inte hittar något
                        st.warning("Kunde inte hitta ett giltigt JSON-block i svaret.")
                        st.write(json_res)
                except json.JSONDecodeError:
                    st.warning("Kunde inte tolka JSON-svaret, även efter rensning.")
                    st.write(json_res)
                except Exception as e:
                    st.error(f"Ett oväntat fel uppstod: {e}")
                    st.write(json_res)
 
        cards = st.session_state.flashcards.get(st.session_state.current_subject) 
        if cards: 
            for i, card in enumerate(cards): 
                with st.expander(f"Kort {i+1}: {card['question']}"): 
                    st.write(f"**Svar:** {card['answer']}") 
 
    # FLIK 4 
    with tab4: 
        st.subheader("Ljudbok") 
        txt_speech = st.text_area("Text att läsa:", value=material_text[:2000], height=150) 
        if st.button("▶️ Spela upp"): 
            with st.spinner("Genererar ljud..."): 
                audio = generate_speech_simple(txt_speech) 
                if audio: 
                    st.audio(audio) 
                    
# --- 7. KONFIGURATION & FELSÖKNING ---
# (Behövs inte för grundläggande funktion, men kan vara bra för framtiden)
# st.sidebar.divider()
# st.sidebar.subheader("Inställningar")
# st.sidebar.checkbox("Använd Gemini Pro Vision (för bilder)")
# ... fler inställningar kan läggas till här ...