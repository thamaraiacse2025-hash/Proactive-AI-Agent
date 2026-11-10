
import sqlite3
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# 1. Database Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"


# 2. Get User Skills
skills_input = input(
    "Enter your skills (comma-separated): "
).strip()

user_skills = [
    skill.strip()
    for skill in skills_input.split(",")
    if skill.strip()
]

if not user_skills:
    print("Please enter at least one skill.")
    raise SystemExit


# 3. Connect to Database
connection = None

try:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT job_title, company, location, apply_link, description
        FROM jobs
    """)

    jobs = cursor.fetchall()

    if not jobs:
        print("No internships available in the database.")
        raise SystemExit

    print("\nYour skills:", ", ".join(user_skills))
    print("Total internships available:", len(jobs))


    # 4. Load Semantic AI Model
    print("\nLoading semantic AI model...")

    model = SentenceTransformer("all-MiniLM-L6-v2")


    # 5. Prepare Internship Text
    job_texts = []

    for job in jobs:
        title = job[0] or ""
        company = job[1] or ""
        location = job[2] or ""
        description = job[4] or ""

        combined_text = (
            f"Internship title: {title}. "
            f"Company: {company}. "
            f"Location: {location}. "
            f"Job description and qualifications: {description}"
        )

        job_texts.append(combined_text)


    # 6. Generate Text Embeddings
    print("Generating text embeddings...")

    skill_embeddings = model.encode(
        user_skills,
        normalize_embeddings=True
    )

    job_embeddings = model.encode(
        job_texts,
        normalize_embeddings=True
    )


    # 7. Calculate Semantic Similarity
    recommendations = []

    for index, job in enumerate(jobs):

        similarities = cosine_similarity(
            skill_embeddings,
            job_embeddings[index].reshape(1, -1)
        ).flatten()

        average_similarity = float(similarities.mean())

        matched_skills = [
            user_skills[i]
            for i, similarity in enumerate(similarities)
            if similarity > 0.25
        ]

        recommendations.append({
            "job": job,
            "score": average_similarity,
            "matched_skills": matched_skills
        })


    # 8. Rank Recommendations
    recommendations.sort(
        key=lambda item: item["score"],
        reverse=True
    )


    # 9. Display Recommendations
    print("\n--- AI Semantic Recommendations ---")

    for rank, item in enumerate(recommendations, start=1):

        job = item["job"]
        score = item["score"]
        matched_skills = item["matched_skills"]

        print("\n----------------------------------------")
        print("Rank:", rank)
        print("Title:", job[0])
        print("Company:", job[1])
        print("Location:", job[2])

        print(
            "Related skills:",
            ", ".join(matched_skills)
            if matched_skills
            else "No skills passed the similarity threshold"
        )

        print(
            "Average semantic similarity:",
            f"{score * 100:.2f}%"
        )

        print("Apply link:", job[3])


    # 10. Summary
    print("\n----------------------------------------")
    print("Recommendation process completed.")
    print("Internships ranked:", len(recommendations))


except sqlite3.Error as error:
    print("Database error:", error)

except Exception as error:
    print("Error:", error)

finally:
    if connection:
        connection.close()
