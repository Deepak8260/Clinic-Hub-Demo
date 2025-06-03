import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import json

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
API_KEY = st.secrets["GENAI_API_KEY"]

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure Generative AI
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# --------------------------------------------
# 🔹 Function to fetch doctor data from Supabase
# --------------------------------------------

def fetch_doctor_data():
    """Fetch all relevant doctor info from Supabase tables."""
    # Fetch doctors
    doctors_res = supabase.table("doctors").select("*").execute()
    doctors = doctors_res.data or []

    # Fetch doctor_specializations
    specs_res = supabase.table("doctor_specializations").select("*").execute()
    specializations = specs_res.data or []

    # Fetch doctor_languages
    langs_res = supabase.table("doctor_languages").select("*").execute()
    languages = langs_res.data or []

    # Fetch clinics
    clinics_res = supabase.table("clinics").select("*").execute()
    clinics = clinics_res.data or []

    # Fetch patient_reviews
    reviews_res = supabase.table("patient_reviews").select("*").execute()
    reviews = reviews_res.data or []

    # Fetch similar_specialists
    similar_res = supabase.table("similar_specialists").select("*").execute()
    similar = similar_res.data or []

    # Organize all data by doctor id for easy lookup
    data = {}
    for d in doctors:
        doc_id = d.get("id")
        data[doc_id] = {
            "info": d,
            "specializations": [s["specialization"] for s in specializations if s["doctor_id"] == doc_id],
            "languages_spoken": [l["language"] for l in languages if l["doctor_id"] == doc_id],
            "clinics": [c for c in clinics if c["doctor_id"] == doc_id],
            "patient_reviews": [r for r in reviews if r["doctor_id"] == doc_id],
            "similar_specialists": [s for s in similar if s.get("doctor_id") == doc_id],
        }
    return data

def explain_similarity(doctor_data):
    main_specs = set(doctor_data["doctor"].get("specializations", []))
    similar = doctor_data.get("similar_specialists", [])
    explanation = []

    for specialist in similar:
        spec = specialist.get("specialization", "Unknown specialization")
        name = specialist.get("name", "Unknown specialist")
        if spec in main_specs:
            explanation.append(f"{name} shares specialization in {spec}.")
        else:
            explanation.append(f"{name} specializes in {spec}, which is related or complementary.")
    
    return "\n".join(explanation)


# --------------------------------------------
# 🔹 System Prompt Template for AI
# --------------------------------------------

def build_system_prompt(doctor_data):
    """Construct the system prompt dynamically using doctor_data."""

    # For example, just use first doctor for demo
    if not doctor_data:
        return "No doctor data found in database."

    # Pick first doctor data
    first_doc = next(iter(doctor_data.values()))

    # Prepare doctor info string
    doc_info = first_doc["info"]
    degrees = ", ".join(first_doc.get("specializations", []))
    languages = ", ".join(first_doc.get("languages_spoken", []))
    clinics = first_doc.get("clinics", [])
    clinics_info = "\n".join([f"- {c.get('name')} ({c.get('location', 'N/A')}), Fee: {c.get('fee', 'N/A')}" for c in clinics])

    
    patient_reviews = doctor_data.get("patient_reviews", [])
    valid_ratings = [r["rating"] for r in patient_reviews if r["rating"] is not None]
    avg_rating = round(sum(valid_ratings) / len(valid_ratings), 2) if valid_ratings else 0
    
    # Build the rest of your prompt with avg_rating...


    prompt = f"""
You are an AI assistant chatbot specialized in providing detailed and professional information about doctors.

Doctor Information:
- Name: {doc_info.get("name")}
- Degrees: {degrees}
- Experience: {doc_info.get("experience")} years
- Average Rating: {avg_rating}
- Languages Spoken: {languages}
- Clinics:
{clinics_info}

Patient Reviews Summary:
{len(patient_reviews)} reviews available.

You will answer user queries based on this data only. Always be polite and professional.

If the user asks about the doctor's specialties, clinics, experience, or reviews, provide accurate info.
If you don’t know the answer from the data, respond with "I'm sorry, I don't have that information."

Only provide info related to the above data. Do not guess or fabricate.
"""
    return prompt.strip()

# --------------------------------------------
# Streamlit UI Configuration
# --------------------------------------------

st.set_page_config(page_title="Doctor Info Chatbot", layout="wide")
st.title("💬 Doctor Info AI Chatbot")

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Fetch doctor data once per session and cache it
@st.cache_data(show_spinner=True)
def get_doctor_data():
    return fetch_doctor_data()

doctor_data = get_doctor_data()
SYSTEM_PROMPT = build_system_prompt(doctor_data)

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input & AI response handling
user_input = st.chat_input("Ask about the doctor...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Prepare context: last 5 messages + system prompt
    history = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.messages[-5:]])
    prompt = f"{SYSTEM_PROMPT}\n\nConversation:\n{history}\nUser: {user_input}"

    # Generate AI response
    ai_response = model.generate_content(prompt)
    response_text = ai_response.candidates[0].content.parts[0].text if ai_response.candidates else "Sorry, I couldn't generate a response."

    st.session_state.messages.append({"role": "assistant", "content": response_text})
    with st.chat_message("assistant"):
        st.markdown(response_text)
