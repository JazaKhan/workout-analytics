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

# volume analysis

# Calc volume for every weighted set
weighted_df = weighted_df.copy()
weighted_df["set_volume"] = weighted_df["weight_lbs"] * weighted_df["reps"]

volume_by_muscle = weighted_df.groupby("primary_muscle_group")["set_volume"].sum().sort_values(ascending=False)

print("\n--- Total volume by muscle group (weighted exercises only) ---")
print(volume_by_muscle.to_string())

sets_by_muscle = df["primary_muscle_group"].value_counts()

print("\n--- Set count by muscle group (all exercise types) ---")
print(sets_by_muscle.to_string())

# Progression vs. Plateau

def check_plateau(exercise_name, recent_days=120, min_recent_sessions=2):
    ex_df = df[df["exercise_title"] == exercise_name].copy()
    
    progress = ex_df.groupby("date").agg(
        max_weight=("weight_lbs", "max"),
        max_reps_at_peak=("reps", "max")
    ).reset_index().sort_values("date")
    
    progress["date"] = pd.to_datetime(progress["date"])
    
    most_recent_date = progress["date"].max()
    cutoff_date = most_recent_date - pd.Timedelta(days=recent_days)
    
    recent_sessions = progress[progress["date"] > cutoff_date]
    earlier_sessions = progress[progress["date"] <= cutoff_date]
    
    if len(earlier_sessions) == 0 or len(recent_sessions) < min_recent_sessions:
        return None
    
    peak_weight_before = earlier_sessions["max_weight"].max()
    peak_weight_recent = recent_sessions["max_weight"].max()
    peak_reps_before = earlier_sessions["max_reps_at_peak"].max()
    peak_reps_recent = recent_sessions["max_reps_at_peak"].max()
    
    weight_improved = peak_weight_recent > peak_weight_before
    reps_improved = (peak_weight_recent >= peak_weight_before) and (peak_reps_recent > peak_reps_before)
    weight_declined = peak_weight_recent < peak_weight_before
    reps_declined = peak_reps_recent < peak_reps_before
    
    if weight_improved or reps_improved:
        status = "progressing"
    elif weight_declined and reps_declined:
        status = "regressing"
    else:
        status = "plateaued"
    
    return {
        "exercise": exercise_name,
        "sessions_before": len(earlier_sessions),
        "sessions_recent": len(recent_sessions),
        "peak_weight_before": peak_weight_before,
        "peak_weight_recent": peak_weight_recent,
        "peak_reps_before": peak_reps_before,
        "peak_reps_recent": peak_reps_recent,
        "status": status
    }

# print(f"\n--- Progress check across top 15 exercises (last 120 days vs. earlier) ---")
# for exercise in top_exercises:
#     result = check_plateau(exercise)
#     if result is None:
#         print(f"\n{exercise}: not enough sessions to evaluate")
#         continue
    
#     print(f"\n{exercise}: {result['status'].upper()}")
#     print(f"  Sessions: {result['sessions_before']} before, {result['sessions_recent']} in last 90 days")
#     print(f"  Peak weight before: {result['peak_weight_before']} lbs")
#     print(f"  Peak weight recent: {result['peak_weight_recent']} lbs")
#     print(f"  Peak reps before: {result['peak_reps_before']}")
#     print(f"  Peak reps recent: {result['peak_reps_recent']}")

print(f"\n--- Progress check across top 15 exercises (last 120 days vs. earlier) ---")

progress_results = []

for exercise in top_exercises:
    result = check_plateau(exercise)
    if result is None:
        print(f"\n{exercise}: not enough sessions to evaluate")
        continue
    
    progress_results.append(result)
    
    print(f"\n{exercise}: {result['status'].upper()}")
    print(f"  Sessions: {result['sessions_before']} before, {result['sessions_recent']} in last 90 days")
    print(f"  Peak weight before: {result['peak_weight_before']} lbs")
    print(f"  Peak weight recent: {result['peak_weight_recent']} lbs")
    print(f"  Peak reps before: {result['peak_reps_before']}")
    print(f"  Peak reps recent: {result['peak_reps_recent']}")

progress_df = pd.DataFrame(progress_results)
progress_df.to_csv("progress_summary.csv", index=False)
print(f"\nExported progress_summary.csv with {len(progress_df)} rows")

monthly_export = monthly_counts_full.reset_index()
monthly_export.columns = ["month", "training_days"]
monthly_export["month"] = monthly_export["month"].astype(str)
monthly_export.to_csv("monthly_consistency.csv", index=False)
print(f"Exported monthly_consistency.csv with {len(monthly_export)} rows")

# Export cleaned data for Power BI

df.to_csv("cleaned_workouts.csv", index=False)
print(f"\nExported cleaned_workouts.csv with {len(df)} rows")