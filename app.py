import streamlit as st
import openai
import sqlite3
from datetime import datetime, timedelta
from streamlit.runtime.scriptrunner import get_script_run_ctx

# Klucz API OpenAI
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Konfiguracja limitów
QUERY_LIMIT = 20
RESET_HOURS = 24

# Funkcja do uzyskania adresu IP użytkownika
def get_user_ip():
    try:
        # Pobierz kontekst sesji
        ctx = get_script_run_ctx()
        if ctx and "X-Forwarded-For" in ctx.request_headers:
            # Pobierz IP z nagłówków
            return ctx.request_headers.get("X-Forwarded-For", "127.0.0.1").split(",")[0]
        else:
            # Jeśli nagłówki nie są dostępne, użyj adresu lokalnego
            return "127.0.0.1"
    except Exception as e:
        # Obsłuż wszelkie inne błędy i zwróć IP lokalne
        st.error(f"Błąd podczas pobierania adresu IP: {e}")
        return "127.0.0.1"

# Utwórz bazę danych SQLite
def create_database():
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            ip_address TEXT,
            query_count INTEGER DEFAULT 0,
            reset_time TEXT
        )
    """)
    conn.commit()
    conn.close()

# Pobierz dane użytkownika
def get_user_data(user_id):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT query_count, reset_time FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data

# Zaktualizuj dane użytkownika
def update_user_data(user_id, ip_address, query_count, reset_time):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, ip_address, query_count, reset_time)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            query_count = ?,
            reset_time = ?
    """, (user_id, ip_address, query_count, reset_time, query_count, reset_time))
    conn.commit()
    conn.close()

# Funkcja do zapytania agenta
def query_agent(prompt, context):
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )
    return response['choices'][0]['message']['content']

# Inicjalizacja bazy danych
create_database()

# UI w Streamlit
st.title("Python Learning Assistant - demo")
st.write("Dzień dobry Słuchaczu studiów podyplomowych. Jestem asystentem do przedmiotu **'Podstawy programowania w języku Python'**. W czym mogę Ci dzisiaj pomóc?")

# Uzyskaj adres IP użytkownika
user_ip = get_user_ip()

# Obsługa ciasteczek
if "user_id" not in st.session_state:
    # Jeśli brak `user_id` w sesji, przypisz nowy
    user_id = f"{user_ip}_{datetime.now().timestamp()}"
    st.session_state["user_id"] = user_id
else:
    user_id = st.session_state["user_id"]

# Pobierz dane użytkownika
user_data = get_user_data(user_id)
if user_data:
    query_count, reset_time = user_data
    reset_time = datetime.strptime(reset_time, "%Y-%m-%d %H:%M:%S")
else:
    query_count = 0
    reset_time = datetime.now()

# Sprawdź, czy licznik należy zresetować
if datetime.now() > reset_time:
    query_count = 0
    reset_time = datetime.now() + timedelta(hours=RESET_HOURS)

# Wyświetl pozostały limit zapytań
st.write(f"Pozostałe zapytania na dziś: {QUERY_LIMIT - query_count}/{QUERY_LIMIT}")

# Input użytkownika
user_query = st.text_input("Twoje pytanie:")

if st.button("Wyślij"):
    if query_count >= QUERY_LIMIT:
        st.error("Przekroczono dzienny limit zapytań. Spróbuj ponownie za 24 godziny!")
    elif user_query:
        # Zaktualizuj licznik zapytań
        query_count += 1
        update_user_data(user_id, user_ip, query_count, reset_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Uzyskaj odpowiedź od agenta
        context = """
        Jesteś pomocnym asystentem do nauki programowania w języku Python. Odpowiadasz tylko na pytania związane z Pythonem.
        """
        answer = query_agent(user_query, context)
        st.text_area("Odpowiedź:", value=answer, height=300)
    else:
        st.warning("Wpisz pytanie, zanim klikniesz Wyślij!")
