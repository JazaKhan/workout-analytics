import json
import pandas as pd

# Load personal data (pre-cleaned)
df = pd.read_csv("workouts.csv")
your_exercises = df["exercise_title"].unique()

# Load hevy data to compare
with open("hevy_exercise_catalog.json", "r") as f:
    hevy_catalog = json.load(f)

matched = {}
unmatched = []

for exercise in your_exercises:
    if exercise in hevy_catalog:
        matched[exercise] = hevy_catalog[exercise]
    else:
        unmatched.append(exercise)

print(f"Matched: {len(matched)} out of {len(your_exercises)}")
print(f"\nUnmatched exercises ({len(unmatched)}):")
for ex in unmatched:
    print(" -", ex)

# Save matched to muscle_groups.json
with open("muscle_groups.json", "w") as f:
    json.dump(matched, f, indent=2)

print("\nSaved matched exercises to muscle_groups.json")