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
            model="gpt-4",  # lub "gpt-3.5-turbo"
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

# Initialize database
create_database()

# Application UI
st.title("Python Learning Assistant")
st.write("Dzień dobry Słuchaczu studiów podyplomowych. Jestem asystentem do przedmiotu **'Podstawy programowania w języku Python'**. W czym mogę Ci dzisiaj pomóc?")

# Get user ID
user_id = get_user_id()

# Get user data from database
user_data = get_user_data(user_id)
if user_data:
    query_count, reset_time = user_data
    reset_time = datetime.strptime(reset_time, "%Y-%m-%d %H:%M:%S")
else:
    query_count = 0
    reset_time = datetime.now() + timedelta(hours=RESET_HOURS)
    update_user_data(user_id, query_count, reset_time.strftime("%Y-%m-%d %H:%M:%S"))

# Check if query counter should be reset
if datetime.now() > reset_time:
    query_count = 0
    reset_time = datetime.now() + timedelta(hours=RESET_HOURS)
    update_user_data(user_id, query_count, reset_time.strftime("%Y-%m-%d %H:%M:%S"))

# Display remaining query limit
st.write(f"Pozostałe zapytania na dziś: {QUERY_LIMIT - query_count}/{QUERY_LIMIT}")

# User input
user_query = st.text_input("Twoje pytanie:")
if st.button("Wyślij"):
    if query_count >= QUERY_LIMIT:
        st.error("Przekroczono dzienny limit zapytań. Spróbuj ponownie za 24 godziny!")
    elif user_query:
        query_count += 1
        update_user_data(user_id, query_count, reset_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        context = """
        Jesteś pomocnym asystentem do nauki programowania w języku Python. Odpowiadasz tylko na pytania związane z Pythonem.
        """
        answer = query_agent(user_query, context)
        st.text_area("Odpowiedź:", value=answer, height=300)
    else:
        st.warning("Wpisz pytanie, zanim klikniesz Wyślij!")
