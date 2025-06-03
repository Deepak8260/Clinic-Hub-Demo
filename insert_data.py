from supabase import create_client
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    json_file_path = "data.json"  # Make sure this JSON contains the doctor's data

    with open(json_file_path, "r") as f:
        data = json.load(f)

    doctor = data["doctor"]

    degree_str = ", ".join(doctor.get("degrees", []))

    # Convert recommendation_rate "98%" -> 98 integer
    recommendation_raw = doctor.get("recommendation_rate", "")
    recommendation_rate = None
    if recommendation_raw:
        try:
            recommendation_rate = int(recommendation_raw.strip('%'))
        except ValueError:
            recommendation_rate = None

    doctor_data = {
        "name": doctor.get("name"),
        "degree": degree_str,
        "experience": doctor.get("experience"),
        "rating": doctor.get("rating"),
        "reviews_count": doctor.get("reviews_count"),
        "recommendation_rate": recommendation_rate,
        "clinics_count": doctor.get("clinics_count"),
        "about": doctor.get("about")
    }

    response = supabase.table("doctors").insert(doctor_data).execute()
    doctor_id = response.data[0]["id"]

    specializations = [{"doctor_id": doctor_id, "specialization": s} for s in doctor.get("specializations", [])]
    supabase.table("doctor_specializations").insert(specializations).execute()

    languages = [{"doctor_id": doctor_id, "language": lang} for lang in doctor.get("languages_spoken", [])]
    supabase.table("doctor_languages").insert(languages).execute()

    clinics = doctor.get("associated_clinics", [])
    clinics_data = [
        {
            "doctor_id": doctor_id,
            "name": clinic.get("name"),
            "location": clinic.get("location"),
            "fee": clinic.get("fee")  # only if your schema supports this field
        }
        for clinic in clinics
    ]
    if clinics_data:
        supabase.table("clinics").insert(clinics_data).execute()

    reviews = [{"doctor_id": doctor_id, "rating": r.get("rating"), "comment": r.get("comment")} for r in doctor.get("patient_reviews", [])]
    if reviews:
        supabase.table("patient_reviews").insert(reviews).execute()

    similar_specs = data.get("similar_specialists", [])
    if similar_specs:
        supabase.table("similar_specialists").insert(similar_specs).execute()

    print("Data inserted successfully.")

if __name__ == "__main__":
    main()
