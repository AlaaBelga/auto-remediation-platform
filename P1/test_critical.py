import os

import pandas as pd
import requests


columns = (
    ["unit_number", "time_cycle"]
    + [f"op_setting_{i}" for i in range(1, 4)]
    + [f"sensor_{i}" for i in range(1, 22)]
)

df = pd.read_csv("train_FD001.txt", sep=r"\s+", header=None)
df.columns = columns

# Prendre une ligne proche de la fin de vie d'une machine.
machine_id = 1
sample = df[df["unit_number"] == machine_id].tail(1)

features = [f"sensor_{i}" for i in range(1, 22)] + [
    f"op_setting_{i}" for i in range(1, 4)
]
payload = sample[features].iloc[0].to_dict()

api_key = os.getenv("P1_API_KEY") or os.getenv("PLATFORM_API_KEY")
headers = {"X-API-Key": api_key} if api_key else None
response = requests.post(
    "http://127.0.0.1:8000/predict",
    json=payload,
    headers=headers,
    timeout=10,
)

print("Machine testee :", machine_id)
print("Cycle teste :", int(sample["time_cycle"].iloc[0]))
print(response.json())
