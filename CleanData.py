import pandas as pd

df = pd.read_csv("workouts.csv")

print("Shape:", df.shape)
print("\nColumn names:")
print(df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())