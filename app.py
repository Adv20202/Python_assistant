import streamlit as st
from openai import OpenAI
import sqlite3
from datetime import datetime, timedelta

# OpenAI API key configuration
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Configuration limits
QUERY_LIMIT = 20
RESET_HOURS = 24

def create_database():
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            query_count INTEGER DEFAULT 0,
            reset_time TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT query_count, reset_time FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data

def update_user_data(user_id, query_count, reset_time):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, query_count, reset_time)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            query_count = excluded.query_count,
            reset_time = excluded.reset_time
    """, (user_id, query_count, reset_time))
    conn.commit()
    conn.close()

def query_agent(prompt, context):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Błąd API OpenAI: {str(e)}"

def get_user_id():
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = f"user_{datetime.now().timestamp()}"
    return st.session_state["user_id"]

# Customize the Streamlit interface
st.set_page_config(
    page_title="Python Learning Assistant",
    page_icon="🐍",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .st-emotion-cache-1v0mbdj {
        width: 100%;
    }
    .output-container {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    h1 {
        color: #0e1117;
        margin-bottom: 2rem;
    }
    .highlight {
        background-color: #f0f2f6;
        padding: 0.2em 0.4em;
        border-radius: 3px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize database
create_database()

# Application UI
st.title("🐍 Python Learning Assistant")
st.markdown("""
    <div style='background-color: #f0f2f6; padding: 1rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h3 style='margin: 0; color: #0e1117;'>Dzień dobry Słuchaczu studiów podyplomowych!</h3>
        <p style='margin: 0.5rem 0 0 0;'>Jestem asystentem do przedmiotu <b>Podstawy programowania w języku Python</b>. 
        W czym mogę Ci dzisiaj pomóc?</p>
    </div>
""", unsafe_allow_html=True)

# Get user ID and handle data
user_id = get_user_id()
user_data = get_user_data(user_id)

if user_data:
    query_count, reset_time = user_data
    reset_time = datetime.strptime(reset_time, "%Y-%m-%d %H:%M:%S")
else:
    query_count = 0
    reset_time = datetime.now() + timedelta(hours=RESET_HOURS)
    update_user_data(user_id, query_count, reset_time.strftime("%Y-%m-%d %H:%M:%S"))

if datetime.now() > reset_time:
    query_count = 0
    reset_time = datetime.now() + timedelta(hours=RESET_HOURS)
    update_user_data(user_id, query_count, reset_time.strftime("%Y-%m-%d %H:%M:%S"))

# Display remaining queries in a more attractive way
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
        <div style='background-color: #e6f3ff; padding: 1rem; border-radius: 10px;'>
            <p style='margin: 0; color: #0e1117;'>
                <b>Pozostałe zapytania na dziś:</b> {QUERY_LIMIT - query_count}/{QUERY_LIMIT}
            </p>
        </div>
    """, unsafe_allow_html=True)

# User input section
st.markdown("### 💭 Zadaj pytanie")
user_query = st.text_input("", placeholder="Wpisz swoje pytanie dotyczące Pythona...")
send_button = st.button("📤 Wyślij")

if send_button:
    if query_count >= QUERY_LIMIT:
        st.error("❌ Przekroczono dzienny limit zapytań. Spróbuj ponownie za 24 godziny!")
    elif user_query:
        query_count += 1
        update_user_data(user_id, query_count, reset_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        context = """
        Jesteś pomocnym asystentem do nauki programowania w języku Python. 
        Odpowiadasz tylko na pytania związane z Pythonem.
        Formatuj swoje odpowiedzi używając składni Markdown, aby były czytelne i dobrze zorganizowane.
        Używaj emoji 🐍 przy omawianiu kluczowych konceptów Pythona.
        Dla przykładów kodu używaj bloków kodu z odpowiednim podświetlaniem składni.
        """
        
        with st.spinner("🤔 Generuję odpowiedź..."):
            answer = query_agent(user_query, context)
            st.markdown("""
                <div class='output-container'>
                    <h4 style='color: #0e1117; margin-bottom: 1rem;'>📝 Odpowiedź:</h4>
                """, unsafe_allow_html=True)
            st.markdown(answer)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Wpisz pytanie, zanim klikniesz Wyślij!")

# Footer
st.markdown("""
    <div style='margin-top: 3rem; text-align: center; color: #666;'>
        <p>Python Learning Assistant v1.0 | Powered by OpenAI</p>
    </div>
""", unsafe_allow_html=True)
