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


# --- Exclude test/setup data from Dec 25, 2023 ---
# This date shows 84 sets logged in ~5 minutes, physically unrealistic for real
# training. Confirmed this was likely routine-building/app exploration on Hevy's
# free tier, not an actual workout. Excluding to avoid skewing progressive
# overload baselines.
df = df[df["date"] != pd.to_datetime("2023-12-25").date()]

print(f"\nExcluded Dec 25, 2023 test data. New shape: {df.shape}")

# --- Exclude Hip Thrust (Barbell) data entry error ---
# 2024-08-24 shows 151 lbs, wildly inconsistent with surrounding sessions
# (10-15 lbs range). Almost certainly a typo. Excluding this single row.
df = df[~((df["exercise_title"] == "Hip Thrust (Barbell)") & (df["date"] == pd.to_datetime("2024-08-24").date()))]


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

df["primary_muscle_group"] = df["exercise_title"].map(
    lambda ex: muscle_group_map.get(ex, {}).get("primary_muscle_group")
)

print("\n--- Primary muscle group breakdown (from Hevy data) ---")
print(df["primary_muscle_group"].value_counts())

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

# Calc Progressive overload across top exercises

top_exercises = weighted_df["exercise_title"].value_counts().head(15).index.tolist()

print("\n--- Progressive overload summary for top 15 exercises ---")
for exercise in top_exercises:
    progress = get_exercise_progress(exercise)
    first_session = progress.iloc[0]
    last_session = progress.iloc[-1]
    
    weight_change = last_session["max_weight"] - first_session["max_weight"]
    
    print(f"\n{exercise}:")
    print(f"  Sessions logged: {len(progress)}")
    print(f"  First: {first_session['date']} at {first_session['max_weight']} lbs")
    print(f"  Latest: {last_session['date']} at {last_session['max_weight']} lbs")
    print(f"  Change: {weight_change:+.1f} lbs")

# Training consistency over time

# Get one row per unique training day (not per set)
training_days = df[["date"]].drop_duplicates().sort_values("date")
training_days["date"] = pd.to_datetime(training_days["date"])

# Count training days per month
training_days["month"] = training_days["date"].dt.to_period("M")
monthly_counts = training_days.groupby("month").size()

print("\n--- Training days per month ---")
print(monthly_counts.to_string())

print(f"\nTotal unique training days: {len(training_days)}")
print(f"Date range: {training_days['date'].min().date()} to {training_days['date'].max().date()}")

# FFill missed months w/ 0 
full_month_range = pd.period_range(
    start=training_days["date"].min().to_period("M"),
    end=training_days["date"].max().to_period("M"),
    freq="M"
)
monthly_counts_full = monthly_counts.reindex(full_month_range, fill_value=0)

print("\n--- Training days per month (gaps included) ---")
print(monthly_counts_full.to_string())

# Biggest drop-off period(s)
low_activity_months = monthly_counts_full[monthly_counts_full <= 1]
print(f"\n--- Months with 0-1 training days ({len(low_activity_months)} total) ---")
print(low_activity_months.to_string())

# Longest gap between training days (and when?)
training_days_sorted = training_days.sort_values("date").reset_index(drop=True)
training_days_sorted["days_since_last"] = training_days_sorted["date"].diff().dt.days

longest_gap = training_days_sorted["days_since_last"].max()
longest_gap_row = training_days_sorted[training_days_sorted["days_since_last"] == longest_gap]

print(f"\n--- Longest gap between training days ---")
print(f"{longest_gap:.0f} days")
print(longest_gap_row)