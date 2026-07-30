import pandas as pd
import json

# See what data looks like

df = pd.read_csv("workouts.csv")

print("Shape:", df.shape)
print("\nColumn names:")
print(df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())


# Clean data 

# Fixing Date and Time into python objects for easier analysis
df = df.drop(columns=["description", "superset_id", "exercise_notes", "distance_miles", "rpe"])

df["start_time"] = pd.to_datetime(df["start_time"], format="%b %d, %Y, %I:%M %p")
df["end_time"] = pd.to_datetime(df["end_time"], format="%b %d, %Y, %I:%M %p")

df["date"] = df["start_time"].dt.date

print("\n--- After cleaning ---")
print("Shape:", df.shape)
print("\nData types (check date/time is correctly converted to python object):")
print(df.dtypes)
print("\n Top five cleaned rows:")
print(df.head())


# Separating weight/reps based excersises from timed ones for easier analysis

def classify_row(row):
    if pd.notna(row["duration_seconds"]):
        return "timed"
    elif pd.notna(row["reps"]) & pd.notna(row["weight_lbs"]):
        return "weighted" 
    elif pd.notna(row["reps"]):
        return "bodyweight"
    else:
        return "unknown"

df["typeOfExercise"] = df.apply(classify_row, axis=1)

print("\n--- Exercise type breakdown ---")
print(df["typeOfExercise"].value_counts())


# Load Muscle Grouping 

with open("muscle_groups.json", "r") as f:
    muscle_group_map = json.load(f)

df["muscle_group"] = df["exercise_title"].map(muscle_group_map)

print("\n--- Muscle group breakdown ---")
print(df["muscle_group"].value_counts())

print("\n--- Any exercises that didn't get mapped? ---")
print(df[df["muscle_group"].isna()]["exercise_title"].unique())

# Most-logged + weighted exercises
weighted_df = df[df["typeOfExercise"] == "weighted"]

print("\n--- Top 10 most-logged weighted exercises ---")
print(weighted_df["exercise_title"].value_counts().head(15))

def get_exercise_progress(exercise_name):
    ex_df = df[df["exercise_title"] == exercise_name].copy()
    
    # Group by date: get max weight and total volume per session
    progress = ex_df.groupby("date").agg(
        max_weight=("weight_lbs", "max"),
        total_volume=("weight_lbs", lambda x: (x * ex_df.loc[x.index, "reps"]).sum())
    ).reset_index()
    
    progress = progress.sort_values("date")
    return progress

seated_row_progress = get_exercise_progress("Seated Row (Machine)")
print("\n--- Seated Row (Machine) progress over time ---")
print(seated_row_progress)
print("\nTotal sessions logged:", len(seated_row_progress))