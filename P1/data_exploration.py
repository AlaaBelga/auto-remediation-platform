import os

import pandas as pd


os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.getcwd(), ".matplotlib"))

import matplotlib.pyplot as plt


COLUMNS = (
    ["unit", "time"]
    + [f"setting_{i}" for i in range(1, 4)]
    + [f"sensor_{i}" for i in range(1, 22)]
)


df = pd.read_csv("train_FD001.txt", sep=r"\s+", header=None, names=COLUMNS)

print("Apercu des donnees :")
print(df.head())

print("\nInformations generales :")
print(df.info())

print("\nStatistiques :")
print(df.describe())

print("\nNombre de machines :", df["unit"].nunique())
print("Temps max par machine :")
print(df.groupby("unit")["time"].max().head())


machine_1 = df[df["unit"] == 1]

for sensor in ["sensor_2", "sensor_3", "sensor_4"]:
    plt.figure(figsize=(10, 4))
    plt.plot(machine_1["time"], machine_1[sensor])
    plt.title(f"Evolution de {sensor} pour la machine 1")
    plt.xlabel("Temps")
    plt.ylabel(sensor)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"{sensor}_machine_1.png")
    plt.close()

print("\nGraphiques crees : sensor_2_machine_1.png, sensor_3_machine_1.png, sensor_4_machine_1.png")
