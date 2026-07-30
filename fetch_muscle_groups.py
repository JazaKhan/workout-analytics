import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("HEVY_API_KEY")

url = "https://api.hevyapp.com/v1/exercise_templates"
headers = {"api-key": api_key}

all_exercises = {}
page = 1

while True:
    response = requests.get(url, headers=headers, params={"page": page, "pageSize": 100})
    data = response.json()
    
    for ex in data["exercise_templates"]:
        all_exercises[ex["title"]] = {
            "primary_muscle_group": ex["primary_muscle_group"],
            "secondary_muscle_groups": ex["secondary_muscle_groups"]
        }
    
    print(f"Fetched page {page} of {data['page_count']}")
    
    if page >= data["page_count"]:
        break
    page += 1

print(f"\nTotal exercises collected: {len(all_exercises)}")

with open("hevy_exercise_catalog.json", "w") as f:
    json.dump(all_exercises, f, indent=2)

print("Saved to hevy_exercise_catalog.json")