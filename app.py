import streamlit as st
import openai
import sqlite3
from datetime import datetime, timedelta

# Klucz API OpenAI
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Konfiguracja limitów
QUERY_LIMIT = 20
RESET_HOURS = 24

# Utwórz bazę danych SQLite
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

# Pobierz dane użytkownika
def get_user_data(user_id):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT query_count, reset_time FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data

# Zaktualizuj dane użytkownika
def update_user_data(user_id, query_count, reset_time):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, query_count, reset_time)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            query_count = ?,
            reset_time = ?
    """, (user_id, query_count, reset_time, query_count, reset_time))
    conn.commit()
    conn.close()

# Funkcja do obsługi agenta
def query_agent(prompt, context):
    try:
        # Zmiana składni na nową metodę API
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        # Obsługa błędów
        st.error(f"Błąd API OpenAI: {str(e)}")
        return "Przepraszam, wystąpił problem z OpenAI API."

# Funkcja do uzyskania unikalnego ID użytkownika
def get_user_id():
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = f"user_{datetime.now().timestamp()}"
    return st.session_state["user_id"]

# Inicjalizacja bazy danych
create_database()

# UI aplikacji
st.title("Python Learning Assistant")
st.write("Dzień dobry Słuchaczu studiów podyplomowych. Jestem asystentem do przedmiotu **'Podstawy programowania w języku Python'**. W czym mogę Ci dzisiaj pomóc?")

# Pobierz ID użytkownika
user_id = get_user_id()

# Pobierz dane użytkownika z bazy danych
user_data = get_user_data(user_id)
if user_data:
    query_count, reset_time = user_data
    reset_time = datetime.strptime(reset_time, "%Y-%m-%d %H:%M:%S")
else:
    query_count = 0
    reset_time = datetime.now()

# Sprawdź, czy licznik zapytań należy zresetować
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
        update_user_data(user_id, query_count, reset_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Uzyskaj odpowiedź od agenta
        context = """
        Jesteś pomocnym asystentem do nauki programowania w języku Python. Odpowiadasz tylko na pytania związane z Pythonem.
        """
        answer = query_agent(user_query, context)
        st.text_area("Odpowiedź:", value=answer, height=300)
    else:
        st.warning("Wpisz pytanie, zanim klikniesz Wyślij!")
