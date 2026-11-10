import os
import requests
from dotenv import load_dotenv

# Load API credentials from .env
load_dotenv()

api_key = os.getenv("RAPIDAPI_KEY")
api_host = os.getenv("RAPIDAPI_HOST")

url = "https://jsearch.p.rapidapi.com/search-v2"

headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": api_host
}

params = {
    "query": "software developer internship in India",
    "page": "1",
    "num_pages": "1"
}

if not api_key or not api_host:
    print("Error: API credentials missing!")
    print("Please check your .env file.")

else:
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        print("Status Code:", response.status_code)

        if response.status_code == 200:
            data = response.json()
            jobs = data.get("data", {}).get("jobs", [])
            print("Total jobs found:", len(jobs))

            for index, job in enumerate(jobs[:5], start=1):
                print(f"\n--- Job {index} ---")
                print("Title:", job.get("job_title"))
                print("Company:", job.get("employer_name"))
                print("Location:", job.get("job_location"))
                print("Apply Link:", job.get("job_apply_link"))

        else:
            print("API request failed.")
            print("Response:", response.text[:500])

    except requests.RequestException as error:
        print("Connection error:", error)